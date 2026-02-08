import { useState } from 'react';
import {
  Terminal,
  CheckCircle2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface Task {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed';
}

interface TaskProgressProps {
  onOpenComputer?: () => void;
}

const mockTasks: Task[] = [
  {
    id: '1',
    title: '搜集北京各历史时期的关键信息和数据',
    status: 'completed'
  },
  {
    id: '2',
    title: '撰写并整理北京历史调研报告',
    status: 'completed'
  },
  {
    id: '3',
    title: '向用户交付最终报告',
    status: 'completed'
  }
];

export default function TaskProgress({ onOpenComputer }: TaskProgressProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const completedCount = mockTasks.filter(t => t.status === 'completed').length;
  const totalCount = mockTasks.length;

  return (
    <div className="bg-[#1a1a1a]">
      <div className="max-w-3xl mx-auto px-4">
        <div className="px-2">
        {/* Header */}
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center gap-3 p-3 rounded-lg bg-[#1e1e1e] border border-[#333] hover:bg-[#252525] transition-colors text-left"
        >
          <div className="w-8 h-8 rounded-lg bg-[#2a2a2a] flex items-center justify-center flex-shrink-0">
            <Terminal className="w-4 h-4 text-gray-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-gray-300 text-sm">查看 Leon 的计算机</p>
            <p className="text-gray-500 text-xs mt-0.5">Leon 正在使用编辑器</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-gray-500 text-xs">{completedCount} / {totalCount}</span>
            </div>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </div>
        </button>

        {/* Expanded Content */}
        {isExpanded && (
          <div className="mt-2 ml-14 space-y-2 animate-fade-in">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-gray-500">任务进度</span>
              <span className="text-xs text-gray-500">{completedCount} / {totalCount}</span>
            </div>
            
            {mockTasks.map((task) => (
              <div 
                key={task.id}
                className="flex items-start gap-2 text-sm"
              >
                {task.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                ) : task.status === 'in_progress' ? (
                  <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin flex-shrink-0 mt-0.5" />
                ) : (
                  <div className="w-4 h-4 rounded-full border-2 border-gray-600 flex-shrink-0 mt-0.5" />
                )}
                <span className={`${
                  task.status === 'completed' 
                    ? 'text-gray-400 line-through' 
                    : 'text-gray-300'
                }`}>
                  {task.title}
                </span>
              </div>
            ))}

            {/* View Computer Button */}
            <button
              onClick={onOpenComputer}
              className="w-full mt-3 px-3 py-2 rounded-lg bg-[#2a2a2a] hover:bg-[#333] text-gray-300 text-xs transition-colors flex items-center justify-center gap-2"
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>查看计算机</span>
            </button>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
