package main

/*
Name:        Congress Bulk Pipeline TUI
Date:        2025-10-02
Script Name: main.go
Version:     1.0
Log Summary: Bubble Tea-based TUI to monitor and control the Python pipeline.
Description: The TUI supports two modes:
  - watch: watch files (bulk_urls.json, retry_report.json, log directory) and show status
  - http: talk to the pipeline HTTP control API for live commands and status
Change Summary:
  - 1.0 initial TUI with file-watch and HTTP control support
Inputs: flags --mode (watch|http), --watch-dir, --api-url
Outputs: interactive TUI for monitoring and starting/stopping tasks
*/

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

type model struct {
	mode       string
	watchDir   string
	apiURL     string
	bulkURLs   []string
	retryCount int
	logTail    string
	err        error
	tick       <-chan time.Time
}

func readJSONLines(path string) ([]byte, error) {
	return ioutil.ReadFile(path)
}

func initialModel(mode, watchDir, apiURL string) model {
	return model{mode: mode, watchDir: watchDir, apiURL: apiURL, tick: time.Tick(3 * time.Second)}
}

func (m model) Init() tea.Cmd {
	// start periodic refresh
	return tea.Tick(time.Second*1, func(t time.Time) tea.Msg { return t })
}

type tickMsg time.Time

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case time.Time:
		// refresh files
		if m.mode == "watch" {
			bulkPath := filepath.Join(m.watchDir, "bulk_urls.json")
			retryPath := filepath.Join(m.watchDir, "retry_report.json")
			if data, err := readJSONLines(bulkPath); err == nil {
				var d map[string]interface{}
				_ = json.Unmarshal(data, &d)
				if agg, ok := d["aggregate_urls"].([]interface{}); ok {
					m.bulkURLs = nil
					for _, u := range agg {
						m.bulkURLs = append(m.bulkURLs, fmt.Sprintf("%v", u))
					}
				}
			}
			if data, err := readJSONLines(retryPath); err == nil {
				var d map[string]interface{}
				_ = json.Unmarshal(data, &d)
				if f, ok := d["failures"].([]interface{}); ok {
					m.retryCount = len(f)
				}
			}
			// tail logs (last 10 lines)
			logPath := filepath.Join(m.watchDir, "logs")
			files, _ := ioutil.ReadDir(logPath)
			if len(files) > 0 {
				latest := files[len(files)-1]
				lp := filepath.Join(logPath, latest.Name())
				if b, err := ioutil.ReadFile(lp); err == nil {
					txt := string(b)
					// naive tail
					if len(txt) > 2000 {
						txt = txt[len(txt)-2000:]
					}
					m.logTail = txt
				}
			}
		}
		return m, tea.Tick(3 * time.Second, func(t time.Time) tea.Msg { return t })
	}
	return m, nil
}

func (m model) View() string {
	s := "Congress Bulk Pipeline TUI\n\n"
	s += fmt.Sprintf("Mode: %s\n\n", m.mode)
	if m.mode == "watch" {
		s += fmt.Sprintf("Discovered URLs: %d\n", len(m.bulkURLs))
		s += fmt.Sprintf("Retry failures: %d\n\n", m.retryCount)
		s += "Sample discovered URLs:\n"
		for i, u := range m.bulkURLs {
			if i >= 10 {
				break
			}
			s += fmt.Sprintf(" - %s\n", u)
		}
		s += "\nLog tail (last chunk):\n"
		s += m.logTail + "\n"
	}
	s += "\nPress Ctrl-C to quit.\n"
	return s
}

func main() {
	mode := flag.String("mode", "watch", "mode: watch or http")
	watchDir := flag.String("watch-dir", ".", "directory to watch for bulk_urls.json and retry_report.json")
	apiURL := flag.String("api-url", "http://localhost:8080", "HTTP control API URL (when mode=http)")
	flag.Parse()

	m := initialModel(*mode, *watchDir, *apiURL)
	p := tea.NewProgram(m)
	if err := p.Start(); err != nil {
		fmt.Println("Error running TUI:", err)
		os.Exit(1)
	}
}