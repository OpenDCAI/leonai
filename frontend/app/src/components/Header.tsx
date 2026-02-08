import { useState } from 'react';
import {
  PanelLeft,
  ChevronDown,
  Sparkles,
  Share2,
  User,
  MoreHorizontal,
  Copy
} from 'lucide-react';

interface HeaderProps {
  onToggleSidebar: () => void;
  onToggleComputer: () => void;
  computerOpen: boolean;
}

export default function Header({ 
  onToggleSidebar, 
  onToggleComputer, 
  computerOpen
}: HeaderProps) {
  const [showDropdown, setShowDropdown] = useState(false);

  return (
    <header className="h-12 bg-[#1a1a1a] border-b border-[#333] flex items-center justify-between px-4 flex-shrink-0">
      {/* Left Side */}
      <div className="flex items-center gap-2">
        <button 
          onClick={onToggleSidebar}
          className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors"
        >
          <PanelLeft className="w-4 h-4 text-gray-400" />
        </button>
        
        <div className="relative">
          <button 
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-[#2a2a2a] transition-colors"
          >
            <span className="text-white text-sm font-medium">Leon 1.6 Lite</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          
          {showDropdown && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-[#242424] border border-[#333] rounded-lg shadow-xl z-50 animate-fade-in">
              <div className="p-1">
                <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-white text-sm">
                  <Sparkles className="w-4 h-4" />
                  <span>Leon 1.6 Lite</span>
                </button>
                <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-400 text-sm">
                  <Sparkles className="w-4 h-4" />
                  <span>Leon Pro</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-1">
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors">
          <Sparkles className="w-4 h-4" />
          <span>开始免费试用</span>
        </button>
        
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <Share2 className="w-4 h-4 text-gray-400" />
        </button>
        
        <button 
          onClick={onToggleComputer}
          className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
            computerOpen ? 'bg-blue-600 text-white' : 'hover:bg-[#2a2a2a] text-gray-400'
          }`}
        >
          <Copy className="w-4 h-4" />
        </button>
        
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <User className="w-4 h-4 text-gray-400" />
        </button>
        
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <MoreHorizontal className="w-4 h-4 text-gray-400" />
        </button>
      </div>
    </header>
  );
}
