"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const octopusKnowledge = {
  greeting: "Hi! I'm Octo, your OpenGovt guide! 🐙 I can help you understand politicians, votes, and how to use this platform. What would you like to know?",
  
  topics: {
    "how to use": "To use OpenGovt:\n\n1. Browse politicians in the left sidebar\n2. Click on a politician to see their profile and feed\n3. View their voting records, social media posts, and analytics\n4. Comment on feed items to join the discussion\n5. Like content to show support",
    
    "voting records": "Voting records show how politicians voted on bills. Each vote displays:\n- Bill number and title\n- How they voted (YEA/NAY)\n- Vote tallies\n- Bill description\n- Final result (PASSED/FAILED)",
    
    "analytics": "Analytics cards show performance metrics:\n- Party alignment percentage\n- Constituent approval ratings\n- Bills co-sponsored\n- Committee attendance\n- Trend indicators (↗ up, → stable, ↘ down)",
    
    "research": "Research reports are policy analysis from the OpenDiscourse team, showing:\n- Economic impact studies\n- Research findings\n- Methodology used\n- Data sources",
    
    "comments": "You can comment on any feed item! Just:\n1. Click the 💬 Comments button\n2. Type your comment\n3. Press Post or Enter\n\nYou can also like comments from other users.",
    
    "settings": "Customize your experience in Settings:\n- Choose from multiple color themes (Purple Ocean, Professional Blue, Dark Ocean)\n- Adjust font size (Small to Extra Large)\n- Toggle dark mode\n- All changes save automatically!",
    
    "themes": "We have several beautiful themes:\n\n🟣 Purple Ocean (default) - Our mascot theme with rich purple colors\n🔵 Professional Blue - Clean, Facebook-like design\n🌑 Dark Ocean - Easy on the eyes for night browsing\n\nChange themes in Settings!",
  }
};

function getOctopusResponse(message: string): string {
  const lowerMessage = message.toLowerCase();
  
  // Check for greetings
  if (lowerMessage.match(/^(hi|hello|hey|greetings)/)) {
    return octopusKnowledge.greeting;
  }
  
  // Check for help topics
  for (const [keyword, response] of Object.entries(octopusKnowledge.topics)) {
    if (lowerMessage.includes(keyword)) {
      return response;
    }
  }
  
  // Check for specific questions
  if (lowerMessage.includes("politician") || lowerMessage.includes("senator") || lowerMessage.includes("representative")) {
    return "Politicians on OpenGovt have profiles showing their voting history, analytics, and social media. Click on any politician in the sidebar to explore their activity!";
  }
  
  if (lowerMessage.includes("feed")) {
    return "The feed shows all activity from a politician: votes, social media posts, analytics reports, and research. It's automatically populated - politicians can't control what appears!";
  }
  
  if (lowerMessage.includes("party") || lowerMessage.includes("democrat") || lowerMessage.includes("republican")) {
    return "We track politicians from all parties! You'll see color-coded party affiliations: Blue for Democrats, Red for Republicans, and Purple for Independents.";
  }
  
  // Default responses
  const defaultResponses = [
    "Great question! Try asking me about:\n- How to use the platform\n- Voting records\n- Analytics and metrics\n- Research reports\n- Comments and discussions\n- Settings and themes",
    "I'm here to help! You can ask me about politicians, voting records, how to use features, or customize your settings. What interests you?",
    "Hmm, I'm not sure about that specific question. But I can tell you about:\n✓ Platform navigation\n✓ Understanding votes\n✓ Analytics reports\n✓ Commenting and engagement\n✓ Customization options",
  ];
  
  return defaultResponses[Math.floor(Math.random() * defaultResponses.length)];
}

export function OctopusMascot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isAnimating, setIsAnimating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleOpen = () => {
    setIsOpen(true);
    setIsAnimating(true);
    if (messages.length === 0) {
      setMessages([
        { role: "assistant", content: octopusKnowledge.greeting },
      ]);
    }
  };

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    
    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    
    // Simulate typing delay
    setTimeout(() => {
      const response = getOctopusResponse(userMessage);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    }, 500);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Octopus Button */}
      <button
        onClick={handleOpen}
        className={`fixed bottom-6 right-6 w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-purple-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center text-3xl z-50 ${
          isAnimating ? "animate-bounce" : ""
        }`}
        onAnimationEnd={() => setIsAnimating(false)}
        title="Chat with Octo, your OpenGovt guide!"
      >
        🐙
      </button>

      {/* Chat Window */}
      {isOpen && (
        <Card className="fixed bottom-24 right-6 w-96 h-[500px] shadow-2xl z-50 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-500 to-purple-700 text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🐙</span>
              <div>
                <h3 className="font-bold">Octo</h3>
                <p className="text-xs opacity-90">Your OpenGovt Guide</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white hover:bg-white/20 rounded p-1 transition"
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-muted/20">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-card border"
                  }`}
                >
                  {message.role === "assistant" && (
                    <span className="text-lg mr-2">🐙</span>
                  )}
                  <span className="text-sm whitespace-pre-wrap">{message.content}</span>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t bg-background">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything..."
                className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
              />
              <Button
                onClick={handleSend}
                disabled={!inputValue.trim()}
                size="sm"
              >
                Send
              </Button>
            </div>
          </div>
        </Card>
      )}
    </>
  );
}
