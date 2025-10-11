import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Copy, RefreshCw, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{
    text: string;
    score?: number;
    metadata: Record<string, any>;
  }>;
  isLoading?: boolean;
}

interface ChatInterfaceProps {
  className?: string;
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m your knowledge assistant. I can help you search through your indexed documents and answer questions about their content. Try asking me something about your documents!',
      timestamp: new Date(),
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    // Add user message
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    // Add loading assistant message
    const loadingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      const response = await api.sendChatMessage(userMessage.content);

      if (response.success && response.response) {
        // Replace loading message with actual response
        setMessages(prev =>
          prev.map(msg =>
            msg.id === loadingMessage.id
              ? {
                  ...msg,
                  content: response.response!,
                  isLoading: false,
                }
              : msg
          )
        );
      } else {
        // Replace loading message with error
        setMessages(prev =>
          prev.map(msg =>
            msg.id === loadingMessage.id
              ? {
                  ...msg,
                  content: `Sorry, I encountered an error: ${response.error || 'Unknown error'}`,
                  isLoading: false,
                }
              : msg
          )
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      // Replace loading message with error
      setMessages(prev =>
        prev.map(msg =>
          msg.id === loadingMessage.id
            ? {
                ...msg,
                content: `Sorry, I couldn't process your message: ${error instanceof Error ? error.message : 'Unknown error'}`,
                isLoading: false,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      // Focus back on input
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const clearChat = () => {
    setMessages([
      {
        id: '1',
        type: 'assistant',
        content: 'Chat cleared! How can I help you with your documents?',
        timestamp: new Date(),
      }
    ]);
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.type === 'user';

    return (
      <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`flex items-start space-x-3 max-w-[80%] ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
          {/* Avatar */}
          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
            isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
          }`}>
            {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </div>

          {/* Message Content */}
          <div className={`rounded-lg p-3 ${
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted/50 border'
          }`}>
            {message.isLoading ? (
              <div className="flex items-center space-x-2">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            ) : (
              <>
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>

                {/* Message Actions */}
                {!isUser && (
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(message.content)}
                      className="h-6 px-2"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <MessageSquare className="h-5 w-5" />
            <span>Knowledge Assistant</span>
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={clearChat}
            disabled={isLoading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Clear
          </Button>
        </div>
        <Separator />
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Messages */}
        <ScrollArea className="h-[400px] pr-4" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messages.map(renderMessage)}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="flex space-x-2">
          <Input
            ref={inputRef}
            placeholder="Ask a question about your documents..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInputMessage("What documents do I have?")}
            disabled={isLoading}
          >
            What documents do I have?
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInputMessage("Summarize my latest documents")}
            disabled={isLoading}
          >
            Summarize latest documents
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInputMessage("Find information about...")}
            disabled={isLoading}
          >
            Find information about...
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
