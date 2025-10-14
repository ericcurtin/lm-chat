package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Stream   bool      `json:"stream"`
	Messages []Message `json:"messages"`
	Model    string    `json:"model,omitempty"`
}

type ChatResponse struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
	} `json:"choices"`
}

type ModelsResponse struct {
	Data []struct {
		ID string `json:"id"`
	} `json:"data"`
}

type Args struct {
	url               string
	model             string
	command           string
	promptArgs        []string
	prefix            string
	color             string
	apiKey            string
	initialConnection bool
}

type LmChatShell struct {
	conversationHistory []Message
	args                *Args
	requestInProcess    bool
	url                 string
}

func shouldColorize() bool {
	term := os.Getenv("TERM")
	return term != "" && term != "dumb" && isTerminal(os.Stdout)
}

func isTerminal(f *os.File) bool {
	var termios syscall.Termios
	_, _, err := syscall.Syscall6(syscall.SYS_IOCTL, f.Fd(), syscall.TCGETS, uintptr(unsafe.Pointer(&termios)), 0, 0, 0)
	return err == 0
}

func printResponse(response io.Reader, color string) string {
	colorDefault := ""
	colorYellow := ""
	if (color == "auto" && shouldColorize()) || color == "always" {
		colorDefault = "\033[0m"
		colorYellow = "\033[33m"
	}

	fmt.Print("\r")
	assistantResponse := ""
	scanner := bufio.NewScanner(response)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "data: {") {
			jsonLine := line[len("data: "):]
			var chatResp ChatResponse
			if err := json.Unmarshal([]byte(jsonLine), &chatResp); err != nil {
				continue
			}
			if len(chatResp.Choices) > 0 {
				content := chatResp.Choices[0].Delta.Content
				if content != "" {
					fmt.Print(colorYellow + content + colorDefault)
					assistantResponse += content
				}
			}
		}
	}
	fmt.Println()
	return assistantResponse
}

func addAPIKey(args *Args, headers http.Header) http.Header {
	if headers == nil {
		headers = make(http.Header)
	}
	if args.apiKey != "" {
		if len(args.apiKey) < 20 {
			fmt.Println("Warning: Provided API key is invalid.")
		}
		headers.Set("Authorization", "Bearer "+args.apiKey)
	}
	return headers
}

func NewLmChatShell(args *Args) *LmChatShell {
	return &LmChatShell{
		conversationHistory: []Message{},
		args:                args,
		requestInProcess:    false,
		url:                 args.url + "/chat/completions",
	}
}

func (s *LmChatShell) handleArgs() bool {
	var prompt string
	if len(s.args.promptArgs) > 0 {
		prompt = strings.Join(s.args.promptArgs, " ")
	}

	if !isTerminal(os.Stdin) {
		stdinBytes, err := io.ReadAll(os.Stdin)
		if err == nil {
			stdin := string(stdinBytes)
			if prompt != "" {
				prompt += "\n\n" + stdin
			} else {
				prompt = stdin
			}
		}
	}

	if prompt != "" {
		s.defaultHandler(prompt)
		return true
	}

	return false
}

func (s *LmChatShell) defaultHandler(userContent string) bool {
	if userContent == "/bye" || userContent == "exit" {
		return true
	}

	s.conversationHistory = append(s.conversationHistory, Message{
		Role:    "user",
		Content: userContent,
	})
	s.requestInProcess = true
	response := s.request()
	if response == "" {
		return true
	}

	s.conversationHistory = append(s.conversationHistory, Message{
		Role:    "assistant",
		Content: response,
	})
	s.requestInProcess = false
	return false
}

func (s *LmChatShell) makeRequestData() (*http.Request, error) {
	data := ChatRequest{
		Stream:   true,
		Messages: s.conversationHistory,
	}
	if s.args.model != "" {
		data.Model = s.args.model
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", s.url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header = addAPIKey(s.args, req.Header)

	return req, nil
}

func (s *LmChatShell) request() string {
	req, err := s.makeRequestData()
	if err != nil {
		return ""
	}

	client := &http.Client{}
	sleepDuration := 10 * time.Millisecond
	totalTimeSlept := 0.0
	var resp *http.Response

	maxTimeout := 16.0
	if s.args.initialConnection {
		maxTimeout = 30.0
	}

	spinner := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
	spinnerIdx := 0

	for {
		resp, err = client.Do(req)
		if err == nil && resp != nil {
			break
		}

		if isTerminal(os.Stdout) {
			fmt.Printf("\r%s", spinner[spinnerIdx%len(spinner)])
			spinnerIdx++
		}

		if totalTimeSlept > maxTimeout {
			break
		}

		time.Sleep(sleepDuration)
		totalTimeSlept += sleepDuration.Seconds()
		sleepDuration = time.Duration(float64(sleepDuration) * 2)
		if sleepDuration > 100*time.Millisecond {
			sleepDuration = 100 * time.Millisecond
		}

		// Recreate request for retry
		req, _ = s.makeRequestData()
	}

	if resp != nil && resp.StatusCode == http.StatusOK {
		defer resp.Body.Close()
		return printResponse(resp.Body, s.args.color)
	}

	if !s.args.initialConnection {
		fmt.Printf("\rError: could not connect to: %s\n", s.url)
	} else {
		fmt.Printf("Could not connect to: %s\n", s.url)
	}

	return ""
}

func (s *LmChatShell) loop() {
	reader := bufio.NewReader(os.Stdin)
	for {
		s.requestInProcess = false
		fmt.Print(s.args.prefix)
		input, err := reader.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				fmt.Println()
				return
			}
			continue
		}

		input = strings.TrimSpace(input)
		if input == "" {
			continue
		}

		if s.defaultHandler(input) {
			return
		}
	}
}

func listModels(args *Args) error {
	url := args.url + "/models"
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header = addAPIKey(args, req.Header)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	var modelsResp ModelsResponse
	if err := json.NewDecoder(resp.Body).Decode(&modelsResp); err != nil {
		return err
	}

	for _, model := range modelsResp.Data {
		fmt.Println(model.ID)
	}

	return nil
}

func chat(args *Args) int {
	listModelsCmd := args.command == "list" || args.command == "ls"
	if listModelsCmd {
		if err := listModels(args); err != nil {
			fmt.Fprintf(os.Stderr, "Error listing models: %v\n", err)
			return 1
		}
		return 0
	} else if args.command != "run" {
		return 1
	}

	shell := NewLmChatShell(args)
	if shell.handleArgs() {
		return 0
	}

	shell.loop()
	return 0
}

func main() {
	var (
		urlFlag      string
		dmrFlag      bool
		llamacppFlag bool
		ollamaFlag   bool
	)

	flag.StringVar(&urlFlag, "url", "", "Base URL for the model API")
	flag.BoolVar(&dmrFlag, "dmr", false, "Use docker model runner (default: http://127.0.0.1:12434/engines/llama.cpp/v1)")
	flag.BoolVar(&llamacppFlag, "llamacpp", false, "Use llama.cpp server (default: http://127.0.0.1:8080/v1)")
	flag.BoolVar(&ollamaFlag, "ollama", false, "Use ollama server (default: http://127.0.0.1:11434/v1)")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: %s [options] <command> [arguments]\n", os.Args[0])
		fmt.Fprintln(os.Stderr, "\nChat with local models (docker model runner by default).")
		fmt.Fprintln(os.Stderr, "\nCommands:")
		fmt.Fprintln(os.Stderr, "  list, ls              List available models")
		fmt.Fprintln(os.Stderr, "  run <model> [prompt]  Run interactive chat with a model")
		fmt.Fprintln(os.Stderr, "\nOptions:")
		flag.PrintDefaults()
	}

	flag.Parse()

	args := &Args{
		prefix: "> ",
		color:  "auto",
	}

	// Set URL based on selected option
	if urlFlag != "" {
		args.url = urlFlag
	} else if llamacppFlag {
		args.url = "http://127.0.0.1:8080/v1"
	} else if ollamaFlag {
		args.url = "http://127.0.0.1:11434/v1"
	} else {
		// Default to docker model runner
		args.url = "http://127.0.0.1:12434/engines/llama.cpp/v1"
	}

	// Parse command
	remainingArgs := flag.Args()
	if len(remainingArgs) == 0 {
		flag.Usage()
		os.Exit(1)
	}

	args.command = remainingArgs[0]

	if args.command == "run" {
		if len(remainingArgs) < 2 {
			fmt.Fprintln(os.Stderr, "Error: model identifier required for 'run' command")
			flag.Usage()
			os.Exit(1)
		}
		args.model = remainingArgs[1]
		if len(remainingArgs) > 2 {
			args.promptArgs = remainingArgs[2:]
		}
	} else if args.command != "list" && args.command != "ls" {
		fmt.Fprintf(os.Stderr, "Error: unknown command '%s'\n", args.command)
		flag.Usage()
		os.Exit(1)
	}

	exitCode := chat(args)
	if exitCode != 0 {
		flag.Usage()
	}
	os.Exit(exitCode)
}
