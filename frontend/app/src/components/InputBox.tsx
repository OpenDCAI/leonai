import { Mic, Send } from "lucide-react";
import { useRef, useState } from "react";

interface InputBoxProps {
  disabled?: boolean;
  placeholder?: string;
  onSendMessage: (message: string) => Promise<void> | void;
}

export default function InputBox({ disabled = false, placeholder = "发送消息给 Leon", onSendMessage }: InputBoxProps) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  async function handleSend() {
    const text = value.trim();
    if (!text || disabled) return;
    setValue("");
    await onSendMessage(text);
    inputRef.current?.focus();
  }

  return (
    <div className="bg-[#1a1a1a] pb-4">
      <div className="max-w-3xl mx-auto px-4">
        <div className={`flex items-end gap-2 bg-[#2a2a2a] rounded-3xl border transition-all duration-200 ${focused ? "border-blue-500" : "border-[#333]"}`}>
          <div className="flex-1 py-3 pl-4">
            <textarea
              ref={inputRef}
              value={value}
              disabled={disabled}
              onChange={(e) => setValue(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              placeholder={placeholder}
              className="w-full bg-transparent text-white text-sm placeholder-gray-500 resize-none outline-none min-h-[20px] max-h-[120px] disabled:opacity-60"
              rows={1}
            />
          </div>
          <div className="flex items-center gap-1 pr-3 py-3">
            <button className="w-8 h-8 rounded-lg hover:bg-[#333] flex items-center justify-center transition-colors">
              <Mic className="w-5 h-5 text-gray-400" />
            </button>
            <button
              onClick={() => void handleSend()}
              disabled={disabled || !value.trim()}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                !disabled && value.trim() ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-[#333] text-gray-500"
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
