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
	"time"

	tea "github.com/charmbracelet/bubbletea"
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

type Choice struct {
	Delta struct {
		Content string `json:"content"`
	} `json:"delta"`
}

type StreamResponse struct {
	Choices []Choice `json:"choices"`
}

type Model struct {
	ID string `json:"id"`
}

type ModelsResponse struct {
	Data []Model `json:"data"`
}

type Args struct {
	URL        string
	Model      string
	Command    string
	PromptArgs []string
	Prefix     string
	Color      string
	APIKey     string
}

var spinnerChars = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

func shouldColorize() bool {
	term := os.Getenv("TERM")
	return term != "" && term != "dumb" && isTerminal(os.Stdout)
}

func isTerminal(f *os.File) bool {
	fileInfo, err := f.Stat()
	if err != nil {
		return false
	}
	return (fileInfo.Mode() & os.ModeCharDevice) != 0
}

func addAPIKey(args *Args, headers map[string]string) map[string]string {
	if headers == nil {
		headers = make(map[string]string)
	}
	if args.APIKey != "" {
		if len(args.APIKey) < 20 {
			fmt.Println("Warning: Provided API key is invalid.")
		}
		headers["Authorization"] = "Bearer " + args.APIKey
	}
	return headers
}

func printResponse(resp *http.Response, color string) (string, error) {
	colorDefault := ""
	colorYellow := ""
	if (color == "auto" && shouldColorize()) || color == "always" {
		colorDefault = "\033[0m"
		colorYellow = "\033[33m"
	}

	fmt.Print("\r")
	assistantResponse := ""
	scanner := bufio.NewScanner(resp.Body)

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "data: {") {
			jsonStr := strings.TrimPrefix(line, "data: ")
			var streamResp StreamResponse
			if err := json.Unmarshal([]byte(jsonStr), &streamResp); err != nil {
				continue
			}
			if len(streamResp.Choices) > 0 {
				content := streamResp.Choices[0].Delta.Content
				if content != "" {
					fmt.Print(colorYellow + content + colorDefault)
					assistantResponse += content
				}
			}
		}
	}
	fmt.Println()

	if err := scanner.Err(); err != nil {
		return assistantResponse, err
	}

	return assistantResponse, nil
}

func makeRequest(args *Args, conversationHistory []Message) (string, error) {
	reqData := ChatRequest{
		Stream:   true,
		Messages: conversationHistory,
	}
	if args.Model != "" {
		reqData.Model = args.Model
	}

	jsonData, err := json.Marshal(reqData)
	if err != nil {
		return "", err
	}

	url := args.URL + "/chat/completions"

	// Retry logic with spinner
	sleepTime := 0.01
	totalTimeSlept := 0.0
	maxTimeout := 16.0
	spinnerIdx := 0

	var resp *http.Response
	for {
		req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
		if err != nil {
			return "", err
		}

		headers := map[string]string{
			"Content-Type": "application/json",
		}
		headers = addAPIKey(args, headers)
		for k, v := range headers {
			req.Header.Set(k, v)
		}

		resp, err = http.DefaultClient.Do(req)
		if err == nil {
			break
		}

		if isTerminal(os.Stdout) {
			fmt.Print("\r" + spinnerChars[spinnerIdx%len(spinnerChars)])
			spinnerIdx++
		}

		if totalTimeSlept > maxTimeout {
			break
		}

		time.Sleep(time.Duration(sleepTime * float64(time.Second)))
		totalTimeSlept += sleepTime
		sleepTime = min(sleepTime*2, 0.1)
	}

	if resp == nil {
		fmt.Printf("\rError: could not connect to: %s\n", url)
		return "", fmt.Errorf("connection failed")
	}
	defer resp.Body.Close()

	return printResponse(resp, args.Color)
}

func listModels(args *Args) error {
	url := args.URL + "/models"
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	headers := make(map[string]string)
	headers = addAPIKey(args, headers)
	for k, v := range headers {
		req.Header.Set(k, v)
	}

	resp, err := http.DefaultClient.Do(req)
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

type model struct {
	args                *Args
	conversationHistory []Message
	input               string
	cursorPos           int
	err                 error
	quitting            bool
	waitingForResponse  bool
}

type responseMsg struct {
	content string
	err     error
}

func initialModel(args *Args) model {
	return model{
		args:                args,
		conversationHistory: []Message{},
		input:               "",
		cursorPos:           0,
	}
}

func (m model) Init() tea.Cmd {
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if m.waitingForResponse {
			if msg.Type == tea.KeyCtrlC {
				m.quitting = true
				return m, tea.Quit
			}
			return m, nil
		}

		switch msg.Type {
		case tea.KeyCtrlC:
			fmt.Println("\nUse Ctrl + d or /bye or exit to quit.")
			return m, nil
		case tea.KeyCtrlD:
			fmt.Println()
			m.quitting = true
			return m, tea.Quit
		case tea.KeyEnter:
			if m.input == "" {
				return m, nil
			}
			if m.input == "/bye" || m.input == "exit" {
				m.quitting = true
				return m, tea.Quit
			}

			userInput := m.input
			m.input = ""
			m.cursorPos = 0
			m.waitingForResponse = true

			return m, func() tea.Msg {
				m.conversationHistory = append(m.conversationHistory, Message{
					Role:    "user",
					Content: userInput,
				})

				response, err := makeRequest(m.args, m.conversationHistory)
				if err != nil {
					return responseMsg{err: err}
				}

				m.conversationHistory = append(m.conversationHistory, Message{
					Role:    "assistant",
					Content: response,
				})

				return responseMsg{content: response}
			}
		case tea.KeyBackspace:
			if m.cursorPos > 0 {
				m.input = m.input[:m.cursorPos-1] + m.input[m.cursorPos:]
				m.cursorPos--
			}
		case tea.KeyLeft:
			if m.cursorPos > 0 {
				m.cursorPos--
			}
		case tea.KeyRight:
			if m.cursorPos < len(m.input) {
				m.cursorPos++
			}
		case tea.KeyRunes:
			m.input = m.input[:m.cursorPos] + string(msg.Runes) + m.input[m.cursorPos:]
			m.cursorPos += len(msg.Runes)
		}

	case responseMsg:
		m.waitingForResponse = false
		if msg.err != nil {
			m.err = msg.err
			m.quitting = true
			return m, tea.Quit
		}

	case tea.WindowSizeMsg:
		// Handle window resize if needed
		return m, nil
	}

	return m, nil
}

func (m model) View() string {
	if m.quitting {
		return ""
	}

	if m.waitingForResponse {
		return ""
	}

	return m.args.Prefix + m.input
}

func handleDirectPrompt(args *Args, prompt string) error {
	conversationHistory := []Message{
		{Role: "user", Content: prompt},
	}

	response, err := makeRequest(args, conversationHistory)
	if err != nil {
		return err
	}

	_ = response // Response already printed
	return nil
}

func chat(args *Args) error {
	listModelsCmd := args.Command == "list" || args.Command == "ls"

	if listModelsCmd {
		return listModels(args)
	}

	if args.Command != "run" {
		return fmt.Errorf("invalid command")
	}

	// Handle direct prompting
	prompt := strings.Join(args.PromptArgs, " ")

	// Check for stdin input
	if !isTerminal(os.Stdin) {
		stdinBytes, err := io.ReadAll(os.Stdin)
		if err != nil {
			return err
		}
		stdin := string(stdinBytes)
		if prompt != "" {
			prompt = prompt + "\n\n" + stdin
		} else {
			prompt = stdin
		}
	}

	if prompt != "" {
		return handleDirectPrompt(args, prompt)
	}

	// Interactive mode with Bubbletea
	p := tea.NewProgram(initialModel(args))
	m, err := p.Run()
	if err != nil {
		return err
	}

	if finalModel, ok := m.(model); ok && finalModel.err != nil {
		return finalModel.err
	}

	return nil
}

func printHelp() {
	fmt.Println("usage: lm-chat [-h] [--url URL | --dmr | --llamacpp | --ollama] {list,ls,run} ...")
	fmt.Println()
	fmt.Println("Chat with local models (docker model runner by default).")
	fmt.Println()
	fmt.Println("positional arguments:")
	fmt.Println("  {list,ls,run}")
	fmt.Println("    list (ls)           List available models")
	fmt.Println("    run                 Run interactive chat with a model")
	fmt.Println()
	fmt.Println("optional arguments:")
	fmt.Println("  -h, --help            show this help message and exit")
	fmt.Println("  --url URL             Base URL for the model API")
	fmt.Println("  --dmr                 Use docker model runner (default: http://127.0.0.1:12434/engines/llama.cpp/v1)")
	fmt.Println("  --llamacpp            Use llama.cpp server (default: http://127.0.0.1:8080/v1)")
	fmt.Println("  --ollama              Use ollama server (default: http://127.0.0.1:11434/v1)")
}

func main() {
	var urlFlag string
	var dmrFlag bool
	var llamacppFlag bool
	var ollamaFlag bool
	var helpFlag bool

	flag.StringVar(&urlFlag, "url", "", "Base URL for the model API")
	flag.BoolVar(&dmrFlag, "dmr", false, "Use docker model runner")
	flag.BoolVar(&llamacppFlag, "llamacpp", false, "Use llama.cpp server")
	flag.BoolVar(&ollamaFlag, "ollama", false, "Use ollama server")
	flag.BoolVar(&helpFlag, "h", false, "show help message")
	flag.BoolVar(&helpFlag, "help", false, "show help message")

	flag.Parse()

	if helpFlag {
		printHelp()
		os.Exit(0)
	}

	args := &Args{
		Prefix: "> ",
		Color:  "auto",
	}

	// Set URL based on flags
	if urlFlag != "" {
		args.URL = urlFlag
	} else if llamacppFlag {
		args.URL = "http://127.0.0.1:8080/v1"
	} else if ollamaFlag {
		args.URL = "http://127.0.0.1:11434/v1"
	} else {
		// Default to docker model runner
		args.URL = "http://127.0.0.1:12434/engines/llama.cpp/v1"
	}

	// Get API key from environment if available
	args.APIKey = os.Getenv("LM_CHAT_API_KEY")

	// Parse command
	positionalArgs := flag.Args()
	if len(positionalArgs) == 0 {
		printHelp()
		os.Exit(1)
	}

	args.Command = positionalArgs[0]

	if args.Command == "run" {
		if len(positionalArgs) < 2 {
			fmt.Println("error: the following arguments are required: model")
			os.Exit(1)
		}
		args.Model = positionalArgs[1]
		if len(positionalArgs) > 2 {
			args.PromptArgs = positionalArgs[2:]
		}
	}

	if err := chat(args); err != nil {
		if err.Error() == "invalid command" {
			printHelp()
		}
		os.Exit(1)
	}
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}
