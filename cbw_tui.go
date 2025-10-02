package main
/*
Name:        cbw_tui.go
Date:        2025-10-02
Script Name: cbw_tui.go
Version:     1.0
Log Summary: Simple Bubble Tea TUI that watches bulk_urls.json and retry_report.json and displays status.
Description: Minimal TUI to monitor discovery results and retry counts. Use 'go build' to compile.
Change Summary:
  - 1.0 initial watch-mode TUI.
Inputs:
  - flags: --watch-dir (directory containing bulk_urls.json and retry_report.json)
Outputs:
  - interactive terminal UI showing counts and sample urls
*/
import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"path/filepath"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

type model struct {
	watchDir   string
	bulk       []string
	retryCount int
	logTail    string
	err        error
}

func readJSON(path string) ([]byte, error) {
	return ioutil.ReadFile(path)
}

func newModel(watchDir string) model {
	return model{watchDir: watchDir}
}

func (m model) Init() tea.Cmd {
	return tea.Tick(time.Second*2, func(t time.Time) tea.Msg { return t })
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg.(type) {
	case time.Time:
		bulkPath := filepath.Join(m.watchDir, "bulk_urls.json")
		retryPath := filepath.Join(m.watchDir, "retry_report.json")
		if b, err := readJSON(bulkPath); err == nil {
			var d map[string]interface{}
			_ = json.Unmarshal(b, &d)
			if agg, ok := d["aggregate_urls"].([]interface{}); ok {
				m.bulk = nil
				for _, u := range agg {
					m.bulk = append(m.bulk, fmt.Sprintf("%v", u))
				}
			}
		}
		if b, err := readJSON(retryPath); err == nil {
			var d map[string]interface{}
			_ = json.Unmarshal(b, &d)
			if f, ok := d["failures"].([]interface{}); ok {
				m.retryCount = len(f)
			}
		}
		return m, tea.Tick(time.Second*2, func(t time.Time) tea.Msg { return t })
	}
	return m, nil
}

func (m model) View() string {
	s := "cbw Congress Pipeline TUI\n\n"
	s += fmt.Sprintf("Discovered URLs: %d\n", len(m.bulk))
	s += fmt.Sprintf("Retry failures: %d\n\n", m.retryCount)
	s += "Sample URLs:\n"
	for i, u := range m.bulk {
		if i >= 10 {
			break
		}
		s += fmt.Sprintf(" - %s\n", u)
	}
	s += "\nPress Ctrl-C to quit.\n"
	return s
}

func main() {
	watchDir := flag.String("watch-dir", ".", "directory to watch for bulk_urls.json and retry_report.json")
	flag.Parse()
	p := tea.NewProgram(newModel(*watchDir))
	if err := p.Start(); err != nil {
		fmt.Println("Error starting TUI:", err)
	}
}