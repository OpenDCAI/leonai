import { useState, useRef } from 'react';
import {
  Plus,
  Image,
  Link,
  Mic,
  Send
} from 'lucide-react';

interface InputBoxProps {
  onSendMessage?: (message: string) => void;
}

export default function InputBox({ onSendMessage }: InputBoxProps) {
  const [inputValue, setInputValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendMessage?.(inputValue);
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-[#1a1a1a] pb-4">
      <div className="max-w-3xl mx-auto px-4">
        <div 
          className={`flex items-end gap-2 bg-[#2a2a2a] rounded-3xl border transition-all duration-200 ${
            isFocused ? 'border-blue-500' : 'border-[#333]'
          }`}
        >
        {/* Left Tools */}
        <div className="flex items-center gap-1 pl-3 py-3">
          <button className="w-8 h-8 rounded-lg hover:bg-[#333] flex items-center justify-center transition-colors">
            <Plus className="w-5 h-5 text-gray-400" />
          </button>
          <button className="w-8 h-8 rounded-lg hover:bg-[#333] flex items-center justify-center transition-colors">
            <Image className="w-5 h-5 text-gray-400" />
          </button>
          <button className="w-8 h-8 rounded-lg hover:bg-[#333] flex items-center justify-center transition-colors">
            <Link className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Input Area */}
        <div className="flex-1 py-3">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder="发送消息给 Leon"
            className="w-full bg-transparent text-white text-sm placeholder-gray-500 resize-none outline-none min-h-[20px] max-h-[120px]"
            rows={1}
            style={{
              height: 'auto',
              minHeight: '20px'
            }}
          />
        </div>

        {/* Right Tools */}
        <div className="flex items-center gap-1 pr-3 py-3">
          <button className="w-8 h-8 rounded-lg hover:bg-[#333] flex items-center justify-center transition-colors">
            <Mic className="w-5 h-5 text-gray-400" />
          </button>
          <button 
            onClick={handleSend}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
              inputValue.trim() 
                ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                : 'bg-[#333] text-gray-500'
            }`}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        </div>

        {/* Input Tips */}
        {inputValue && (
          <div className="flex items-center gap-2 mt-2 px-2">
            <div className="flex items-center gap-1">
              <span className="text-xs text-green-500 bg-green-500/10 px-1.5 py-0.5 rounded">1</span>
              <span className="text-xs text-gray-500">调研</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-600">2</span>
              <span className="text-xs text-gray-600">北京</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-600">3</span>
              <span className="text-xs text-gray-600">的</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-600">4</span>
              <span className="text-xs text-gray-600">历史</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
