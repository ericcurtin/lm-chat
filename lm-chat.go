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

	"github.com/charmbracelet/huh"
)

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Model    string    `json:"model,omitempty"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream"`
}

type ChatChoice struct {
	Delta struct {
		Content string `json:"content"`
	} `json:"delta"`
}

type ChatResponse struct {
	Choices []ChatChoice `json:"choices"`
}

type Model struct {
	ID string `json:"id"`
}

type ModelsResponse struct {
	Data []Model `json:"data"`
}

type Config struct {
	URL              string
	Model            string
	Command          string
	Args             []string
	APIKey           string
	Prefix           string
	Color            string
	ConversationHistory []Message
}

func shouldColorize() bool {
	term := os.Getenv("TERM")
	return term != "" && term != "dumb" && isTerminal(os.Stdout)
}

func isTerminal(f *os.File) bool {
	stat, _ := f.Stat()
	return (stat.Mode() & os.ModeCharDevice) != 0
}

func printResponse(body io.Reader, color string) (string, error) {
	colorDefault := ""
	colorYellow := ""
	if (color == "auto" && shouldColorize()) || color == "always" {
		colorDefault = "\033[0m"
		colorYellow = "\033[33m"
	}

	fmt.Print("\r")
	var assistantResponse strings.Builder
	scanner := bufio.NewScanner(body)
	
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "data: {") {
			jsonStr := strings.TrimPrefix(line, "data: ")
			var resp ChatResponse
			if err := json.Unmarshal([]byte(jsonStr), &resp); err != nil {
				continue
			}
			
			if len(resp.Choices) > 0 && resp.Choices[0].Delta.Content != "" {
				content := resp.Choices[0].Delta.Content
				fmt.Printf("%s%s%s", colorYellow, content, colorDefault)
				assistantResponse.WriteString(content)
			}
		}
	}
	
	fmt.Println()
	if err := scanner.Err(); err != nil {
		return "", err
	}
	
	return assistantResponse.String(), nil
}

func addAPIKey(config *Config, headers map[string]string) {
	if config.APIKey != "" {
		if len(config.APIKey) < 20 {
			fmt.Println("Warning: Provided API key is invalid.")
		}
		headers["Authorization"] = "Bearer " + config.APIKey
	}
}

func listModels(config *Config) error {
	url := config.URL + "/models"
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	
	headers := make(map[string]string)
	addAPIKey(config, headers)
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	
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

func makeRequest(config *Config) (string, error) {
	url := config.URL + "/chat/completions"
	
	reqData := ChatRequest{
		Model:    config.Model,
		Messages: config.ConversationHistory,
		Stream:   true,
	}
	
	jsonData, err := json.Marshal(reqData)
	if err != nil {
		return "", err
	}
	
	maxRetries := 30
	sleepTime := 10 * time.Millisecond
	spinner := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
	spinnerIdx := 0
	totalSlept := 0 * time.Second
	maxTimeout := 16 * time.Second
	
	var resp *http.Response
	for i := 0; i < maxRetries; i++ {
		req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
		if err != nil {
			return "", err
		}
		
		req.Header.Set("Content-Type", "application/json")
		headers := make(map[string]string)
		addAPIKey(config, headers)
		for k, v := range headers {
			req.Header.Set(k, v)
		}
		
		client := &http.Client{}
		resp, err = client.Do(req)
		if err == nil {
			break
		}
		
		if isTerminal(os.Stdout) {
			fmt.Printf("\r%s", spinner[spinnerIdx%len(spinner)])
			spinnerIdx++
		}
		
		if totalSlept > maxTimeout {
			break
		}
		
		time.Sleep(sleepTime)
		totalSlept += sleepTime
		sleepTime = min(sleepTime*2, 100*time.Millisecond)
	}
	
	if resp == nil {
		return "", fmt.Errorf("could not connect to: %s", url)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("HTTP error: %d", resp.StatusCode)
	}
	
	response, err := printResponse(resp.Body, config.Color)
	if err != nil {
		return "", err
	}
	
	return response, nil
}

func handleDirectPrompt(config *Config, prompt string) error {
	// Check for piped input
	if !isTerminal(os.Stdin) {
		stdinData, err := io.ReadAll(os.Stdin)
		if err == nil && len(stdinData) > 0 {
			if prompt != "" {
				prompt = prompt + "\n\n" + string(stdinData)
			} else {
				prompt = string(stdinData)
			}
		}
	}
	
	if prompt == "" {
		return nil
	}
	
	config.ConversationHistory = append(config.ConversationHistory, Message{
		Role:    "user",
		Content: prompt,
	})
	
	response, err := makeRequest(config)
	if err != nil {
		fmt.Printf("\rError: %v\n", err)
		return err
	}
	
	config.ConversationHistory = append(config.ConversationHistory, Message{
		Role:    "assistant",
		Content: response,
	})
	
	return nil
}

func interactiveLoop(config *Config) error {
	for {
		var userInput string
		
		// Use huh.NewInput for text input in the interactive loop
		err := huh.NewInput().
			Title(strings.TrimSpace(config.Prefix)).
			Value(&userInput).
			Run()
		
		if err != nil {
			// Handle Ctrl+C or Ctrl+D
			if err == huh.ErrUserAborted {
				fmt.Println()
				return nil
			}
			return err
		}
		
		userInput = strings.TrimSpace(userInput)
		
		// Handle exit commands
		if userInput == "/bye" || userInput == "exit" {
			return nil
		}
		
		if userInput == "" {
			continue
		}
		
		config.ConversationHistory = append(config.ConversationHistory, Message{
			Role:    "user",
			Content: userInput,
		})
		
		response, err := makeRequest(config)
		if err != nil {
			fmt.Printf("\rError: %v\n", err)
			continue
		}
		
		config.ConversationHistory = append(config.ConversationHistory, Message{
			Role:    "assistant",
			Content: response,
		})
	}
}

func main() {
	// Define flags
	var (
		urlFlag      = flag.String("url", "", "Base URL for the model API")
		_            = flag.Bool("dmr", false, "Use docker model runner (default: http://127.0.0.1:12434/engines/llama.cpp/v1)")
		llamacppFlag = flag.Bool("llamacpp", false, "Use llama.cpp server (default: http://127.0.0.1:8080/v1)")
		ollamaFlag   = flag.Bool("ollama", false, "Use ollama server (default: http://127.0.0.1:11434/v1)")
	)
	
	flag.Parse()
	
	args := flag.Args()
	if len(args) == 0 {
		fmt.Println("Usage: lm-chat [--url URL | --dmr | --llamacpp | --ollama] <command> [args...]")
		fmt.Println("\nCommands:")
		fmt.Println("  list, ls          List available models")
		fmt.Println("  run <model> [prompt...]  Run interactive chat with a model")
		os.Exit(1)
	}
	
	command := args[0]
	
	config := &Config{
		Command:             command,
		Prefix:              "> ",
		Color:               "auto",
		ConversationHistory: []Message{},
	}
	
	// Set URL based on flags
	if *urlFlag != "" {
		config.URL = *urlFlag
	} else if *llamacppFlag {
		config.URL = "http://127.0.0.1:8080/v1"
	} else if *ollamaFlag {
		config.URL = "http://127.0.0.1:11434/v1"
	} else {
		// Default to docker model runner
		config.URL = "http://127.0.0.1:12434/engines/llama.cpp/v1"
	}
	
	// Handle commands
	if command == "list" || command == "ls" {
		if err := listModels(config); err != nil {
			fmt.Printf("Error listing models: %v\n", err)
			os.Exit(1)
		}
		return
	}
	
	if command == "run" {
		if len(args) < 2 {
			fmt.Println("Error: model identifier required for 'run' command")
			fmt.Println("Usage: lm-chat run <model> [prompt...]")
			os.Exit(1)
		}
		
		config.Model = args[1]
		
		// Check if there are additional arguments (direct prompt)
		if len(args) > 2 {
			prompt := strings.Join(args[2:], " ")
			if err := handleDirectPrompt(config, prompt); err != nil {
				os.Exit(1)
			}
			return
		}
		
		// Check for piped input
		if !isTerminal(os.Stdin) {
			stdinData, err := io.ReadAll(os.Stdin)
			if err == nil && len(stdinData) > 0 {
				if err := handleDirectPrompt(config, string(stdinData)); err != nil {
					os.Exit(1)
				}
				return
			}
		}
		
		// Enter interactive mode
		if err := interactiveLoop(config); err != nil {
			fmt.Printf("Error: %v\n", err)
			os.Exit(1)
		}
		return
	}
	
	fmt.Printf("Unknown command: %s\n", command)
	fmt.Println("Use 'list' or 'run' command")
	os.Exit(1)
}

func min(a, b time.Duration) time.Duration {
	if a < b {
		return a
	}
	return b
}
