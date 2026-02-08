import { useState } from 'react';
import {
  Plus,
  Search,
  Library,
  Folder,
  FileText,
  Settings,
  Filter,
  MoreHorizontal,
  Sparkles,
  ChevronRight
} from 'lucide-react';

interface Task {
  id: string;
  title: string;
  icon?: string;
  active?: boolean;
}

const tasks: Task[] = [
  { id: '1', title: 'hi', active: true },
  { id: '2', title: 'Cloud Code如何通过JSON传递Sy...' },
  { id: '3', title: '讲一下你的沙盒的listdir' },
  { id: '4', title: '虚拟机能安装软件吗' },
  { id: '5', title: 'Alan Turing Computing Machinery...' },
  { id: '6', title: '制作老师及职务信息表格' },
  { id: '7', title: '爬取导师信息生成教师表' },
  { id: '8', title: '如何绘制一个PPT' },
  { id: '9', title: '如何创建工作流服务菜单与筛选需求' },
  { id: '10', title: '如何将证据zip内容整理为Markdow...' },
  { id: '11', title: '如何用超级搜索模式提升qianliu平...' },
  { id: '12', title: '爬取JSON数据对应网站大纲并生成...' },
];

interface SidebarProps {
  onSearchClick: () => void;
  collapsed?: boolean;
}

export default function Sidebar({ onSearchClick, collapsed = false }: SidebarProps) {
  const [activeTask, setActiveTask] = useState('1');

  if (collapsed) {
    return (
      <div className="w-14 h-full bg-[#1e1e1e] border-r border-[#333] flex flex-col items-center py-3 animate-slide-in">
        <div className="mb-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        </div>
        <button className="w-10 h-10 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center mb-2 transition-colors">
          <Plus className="w-5 h-5 text-gray-400" />
        </button>
        <button 
          onClick={onSearchClick}
          className="w-10 h-10 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center mb-2 transition-colors"
        >
          <Search className="w-5 h-5 text-gray-400" />
        </button>
        <button className="w-10 h-10 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center mb-2 transition-colors">
          <Library className="w-5 h-5 text-gray-400" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-[260px] h-full bg-[#1e1e1e] border-r border-[#333] flex flex-col animate-slide-in">
      {/* Logo */}
      <div className="px-3 py-3 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <span className="text-white font-medium text-sm">Leon</span>
      </div>

      {/* Main Navigation */}
      <div className="px-2 py-2 space-y-1">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-300 hover:text-white transition-colors text-sm">
          <Plus className="w-4 h-4" />
          <span>新建任务</span>
        </button>
        <button 
          onClick={onSearchClick}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-300 hover:text-white transition-colors text-sm"
        >
          <Search className="w-4 h-4" />
          <span>搜索</span>
          <span className="ml-auto text-xs text-gray-500">⌘K</span>
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-300 hover:text-white transition-colors text-sm">
          <Library className="w-4 h-4" />
          <span>库</span>
        </button>
      </div>

      {/* Projects Section */}
      <div className="px-2 py-2">
        <div className="flex items-center justify-between px-3 mb-1">
          <span className="text-xs text-gray-500 font-medium">项目</span>
          <button className="w-5 h-5 rounded hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
            <Plus className="w-3 h-3 text-gray-500" />
          </button>
        </div>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-300 hover:text-white transition-colors text-sm">
          <Folder className="w-4 h-4" />
          <span>新项目</span>
        </button>
      </div>

      {/* All Tasks Section */}
      <div className="flex-1 flex flex-col min-h-0 px-2">
        <div className="flex items-center justify-between px-3 mb-1">
          <span className="text-xs text-gray-500 font-medium">所有任务</span>
          <button className="w-5 h-5 rounded hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
            <Filter className="w-3 h-3 text-gray-500" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto space-y-0.5">
          {tasks.map((task) => (
            <button
              key={task.id}
              onClick={() => setActiveTask(task.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-all text-sm group ${
                activeTask === task.id
                  ? 'bg-[#3a3a3a] text-white'
                  : 'text-gray-400 hover:bg-[#2a2a2a] hover:text-gray-300'
              }`}
            >
              <FileText className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{task.title}</span>
              <button className="ml-auto opacity-0 group-hover:opacity-100 w-5 h-5 rounded hover:bg-[#444] flex items-center justify-center transition-all">
                <MoreHorizontal className="w-3 h-3" />
              </button>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="p-2 border-t border-[#333]">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-300 hover:text-white transition-colors text-sm">
          <div className="w-5 h-5 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-3 h-3 text-white" />
          </div>
          <span>与好友分享 Leon</span>
          <ChevronRight className="w-4 h-4 ml-auto text-gray-500" />
        </button>
        <div className="px-3 py-1 text-xs text-gray-500">
          获得 500 积分
        </div>
      </div>

      {/* Bottom Icons */}
      <div className="px-3 py-2 flex items-center gap-1 border-t border-[#333]">
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <Settings className="w-4 h-4 text-gray-500" />
        </button>
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <div className="w-4 h-4 rounded bg-gray-600" />
        </button>
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <div className="w-4 h-4 rounded bg-gray-600" />
        </button>
      </div>
    </div>
  );
}
