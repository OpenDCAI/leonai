import { useState, useEffect, useRef } from 'react';
import {
  Search,
  X,
  FileText
} from 'lucide-react';

interface SearchResult {
  id: string;
  title: string;
  description: string;
  date: string;
  group: string;
}

const searchResults: SearchResult[] = [
  {
    id: '1',
    title: '新建任务',
    description: '开始一个新的对话任务',
    date: '',
    group: '快捷操作'
  },
  {
    id: '2',
    title: 'hi',
    description: '你好！有什么可以帮助你的吗？',
    date: '13:11',
    group: '今天'
  },
  {
    id: '3',
    title: 'Cloud Code如何通过JSON传递System Prompt?',
    description: '这是一个非常好的问题，也是很多人初次接触 JSON 时会有的困惑...',
    date: '星期三',
    group: '今天'
  },
  {
    id: '4',
    title: '讲一下你的沙盒的listdir',
    description: '真相大白了！根据刚才的探测结果，Leon 的方案可能出乎您的意料...',
    date: '星期三',
    group: '过去7天'
  },
  {
    id: '5',
    title: '虚拟机能安装软件吗',
    description: '您的直觉非常精准！通过这组深度探测命令，我们终于揭开了这个沙箱环境的"真面目"。**结论**：我...',
    date: '星期一',
    group: '过去7天'
  },
  {
    id: '6',
    title: '制作老师及职务信息表格',
    description: '我将为您创建一个包含老师姓名、职务、联系方式等信息的表格...',
    date: '上周',
    group: '更早的'
  },
  {
    id: '7',
    title: '如何绘制一个PPT',
    description: '我可以帮您创建一个专业的PPT演示文稿，包括设计布局、内容组织等...',
    date: '上周',
    group: '更早的'
  }
];

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % filteredResults.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filteredResults.length) % filteredResults.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredResults[selectedIndex]) {
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, query]);

  const filteredResults = query 
    ? searchResults.filter(r => 
        r.title.toLowerCase().includes(query.toLowerCase()) ||
        r.description.toLowerCase().includes(query.toLowerCase())
      )
    : searchResults;

  const groupedResults = filteredResults.reduce((acc, result) => {
    if (!acc[result.group]) {
      acc[result.group] = [];
    }
    acc[result.group].push(result);
    return acc;
  }, {} as Record<string, SearchResult[]>);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-[600px] max-h-[500px] bg-[#242424] border border-[#333] rounded-xl shadow-2xl overflow-hidden animate-fade-in">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#333]">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="搜索任务..."
            className="flex-1 bg-transparent text-white text-sm placeholder-gray-500 outline-none"
          />
          <button 
            onClick={onClose}
            className="w-6 h-6 rounded hover:bg-[#333] flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto py-2">
          {Object.entries(groupedResults).map(([group, results]) => (
            <div key={group}>
              <div className="px-4 py-1.5 text-xs text-gray-500 font-medium">
                {group}
              </div>
              {results.map((result) => {
                const globalIndex = filteredResults.findIndex(r => r.id === result.id);
                const isSelected = globalIndex === selectedIndex;
                
                return (
                  <button
                    key={result.id}
                    onClick={() => {
                      onClose();
                    }}
                    className={`w-full px-4 py-2.5 flex items-start gap-3 transition-colors ${
                      isSelected ? 'bg-[#2a2a2a]' : 'hover:bg-[#2a2a2a]'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-lg bg-[#1e1e1e] flex items-center justify-center flex-shrink-0 mt-0.5">
                      <FileText className="w-4 h-4 text-gray-400" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-white text-sm font-medium">{result.title}</p>
                      {result.description && (
                        <p className="text-gray-500 text-xs mt-0.5 line-clamp-1">{result.description}</p>
                      )}
                    </div>
                    {result.date && (
                      <span className="text-gray-500 text-xs flex-shrink-0">{result.date}</span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
          
          {filteredResults.length === 0 && (
            <div className="px-4 py-8 text-center">
              <p className="text-gray-500 text-sm">未找到匹配的结果</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[#333] flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-[#333] text-gray-400">↑</kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-[#333] text-gray-400">↓</kbd>
              <span>导航</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-[#333] text-gray-400">↵</kbd>
              <span>选择</span>
            </span>
          </div>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 rounded bg-[#333] text-gray-400">Esc</kbd>
            <span>关闭</span>
          </span>
        </div>
      </div>
    </div>
  );
}
