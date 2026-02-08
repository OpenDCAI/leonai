import { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  ChevronDown,
  Bot,
  Plus,
  Star
} from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  showThinking?: boolean;
  timestamp?: string;
}

const initialMessages: Message[] = [
  {
    id: '1',
    role: 'user',
    content: 'hi',
    timestamp: '13:11'
  },
  {
    id: '2',
    role: 'assistant',
    content: '你好！有什么可以帮助你的吗？',
    thinking: '用户发送了简单的问候语"hi"，我应该友好地回应并询问他们需要什么帮助。',
    showThinking: false,
    timestamp: '13:11'
  }
];

const followUpQuestions = [
  '详细分析"状态同步"方案的优缺点',
  '对比"状态同步"和"云盘挂载"两种方案的性能',
  '解释"statesync"如何实现增量同步和按需下载'
];

interface ChatAreaProps {
  onOpenComputer?: () => void;
}

export default function ChatArea({ onOpenComputer }: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Use the prop to avoid unused variable warning
  const handleOpenComputer = () => {
    onOpenComputer?.();
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const toggleThinking = (id: string) => {
    setMessages(messages.map(msg => 
      msg.id === id ? { ...msg, showThinking: !msg.showThinking } : msg
    ));
  };

  return (
    <div className="flex-1 overflow-y-auto py-6">
      <div className="max-w-3xl mx-auto px-4 space-y-6">
      {messages.map((message, index) => (
        <div 
          key={message.id}
          className={`animate-fade-in ${index === 0 ? '' : ''}`}
          style={{ animationDelay: `${index * 50}ms` }}
        >
          {message.role === 'user' ? (
            // User Message
            <div className="flex justify-end">
              <div className="max-w-[80%] bg-[#2a2a2a] rounded-2xl px-4 py-2.5">
                <p className="text-white text-sm">{message.content}</p>
              </div>
              {message.timestamp && (
                <span className="text-xs text-gray-500 ml-2 self-end">{message.timestamp}</span>
              )}
            </div>
          ) : (
            // AI Message
            <div className="flex gap-3">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Sparkles className="w-3.5 h-3.5 text-white" />
              </div>
              <div className="flex-1 max-w-[calc(100%-40px)]">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-white text-sm font-medium">Leon</span>
                  <span className="px-1.5 py-0.5 rounded bg-[#333] text-gray-400 text-xs">Lite</span>
                </div>
                
                {/* Thinking Process */}
                {message.thinking && (
                  <div className="mb-2">
                    <button 
                      onClick={() => toggleThinking(message.id)}
                      className="flex items-center gap-1 text-gray-500 text-xs hover:text-gray-400 transition-colors"
                    >
                      <span>思考过程</span>
                      <ChevronDown className={`w-3 h-3 transition-transform ${message.showThinking ? 'rotate-180' : ''}`} />
                    </button>
                    {message.showThinking && (
                      <div className="mt-1 p-2 bg-[#1e1e1e] rounded-lg border border-[#333] text-gray-500 text-xs animate-fade-in">
                        {message.thinking}
                      </div>
                    )}
                  </div>
                )}
                
                {/* Message Content */}
                <div className="markdown-content text-gray-200 text-sm">
                  {message.content}
                </div>
                
                {/* Action Buttons */}
                <div className="flex items-center gap-2 mt-3">
                  <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#2a2a2a] hover:bg-[#333] text-gray-300 text-xs transition-colors">
                    <Bot className="w-3.5 h-3.5" />
                    <span>开启 Agent</span>
                  </button>
                  <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#2a2a2a] hover:bg-[#333] text-gray-300 text-xs transition-colors">
                    <Plus className="w-3.5 h-3.5" />
                    <span>创建</span>
                    <ChevronDown className="w-3 h-3" />
                  </button>
                </div>
                
                {/* Feedback */}
                <div className="flex items-center justify-between mt-4 py-2 border-t border-[#333]">
                  <span className="text-gray-500 text-xs">Leon 解答您的问题效果如何？</span>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button key={star} className="w-5 h-5 flex items-center justify-center text-gray-600 hover:text-yellow-500 transition-colors">
                        <Star className="w-4 h-4" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
      
      {/* Follow-up Questions */}
      <div className="pl-9 space-y-2">
        <p className="text-gray-500 text-xs mb-2">推荐追问</p>
        {followUpQuestions.map((question, index) => (
          <button 
            key={index}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[#1e1e1e] hover:bg-[#2a2a2a] text-gray-300 text-sm transition-colors group"
          >
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full border border-gray-600 group-hover:border-gray-500" />
              <span>{question}</span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-600 rotate-[-90deg]" />
          </button>
        ))}
      </div>
      
      <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
