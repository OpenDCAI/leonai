import { Send } from "lucide-react";
import { useRef, useState } from "react";

interface InputBoxProps {
  disabled?: boolean;
  placeholder?: string;
  onSendMessage: (message: string) => Promise<void> | void;
}

export default function InputBox({ disabled = false, placeholder = "告诉 Leon 你需要什么帮助...", onSendMessage }: InputBoxProps) {
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
    <div className="bg-white pb-4">
      <div className="max-w-3xl mx-auto px-4">
        <div
          className={`flex items-end gap-2 rounded-2xl border transition-all ${
            focused ? "border-[#171717] shadow-sm" : "border-[#e5e5e5]"
          }`}
        >
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
              className="w-full bg-transparent text-sm resize-none outline-none min-h-[20px] max-h-[120px] text-[#171717] placeholder:text-[#a3a3a3] disabled:opacity-50"
              rows={1}
            />
          </div>
          <div className="flex items-center pr-3 py-3">
            <button
              onClick={() => void handleSend()}
              disabled={disabled || !value.trim()}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                !disabled && value.trim()
                  ? "bg-[#171717] text-white hover:bg-[#404040]"
                  : "bg-[#f5f5f5] text-[#d4d4d4]"
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
