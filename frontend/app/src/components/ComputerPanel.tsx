import { useState } from 'react';
import {
  X,
  Copy,
  Maximize2,
  Minimize2,
  Globe,
  Terminal,
  Loader2,
  FileText,
  Folder,
  ChevronRight,
  ChevronDown,
  FolderOpen
} from 'lucide-react';

interface ComputerPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  size?: string;
  path: string;
  children?: FileNode[];
  content?: string;
}

// Mock file system data
const mockFileSystem: FileNode[] = [
  {
    name: 'src',
    type: 'folder',
    path: '/workspace/src',
    children: [
      { name: 'index.ts', type: 'file', size: '3.2 KB', path: '/workspace/src/index.ts', content: 'import express from "express";\n\nconst app = express();\nconst PORT = 3000;\n\napp.get("/", (req, res) => {\n  res.json({ message: "Hello World!" });\n});\n\napp.listen(PORT, () => {\n  console.log(`Server running on port ${PORT}`);\n});' },
      { name: 'utils.ts', type: 'file', size: '1.8 KB', path: '/workspace/src/utils.ts', content: 'export function formatDate(date: Date): string {\n  return date.toISOString();\n}\n\nexport function debounce(fn: Function, ms: number) {\n  let timer: NodeJS.Timeout;\n  return (...args: any[]) => {\n    clearTimeout(timer);\n    timer = setTimeout(() => fn(...args), ms);\n  };\n}' },
      { name: 'types.ts', type: 'file', size: '0.9 KB', path: '/workspace/src/types.ts', content: 'export interface User {\n  id: string;\n  name: string;\n  email: string;\n  createdAt: Date;\n}\n\nexport interface Post {\n  id: string;\n  title: string;\n  content: string;\n  authorId: string;\n}' }
    ]
  },
  {
    name: 'tests',
    type: 'folder',
    path: '/workspace/tests',
    children: [
      { name: 'index.test.ts', type: 'file', size: '2.1 KB', path: '/workspace/tests/index.test.ts', content: 'import { describe, it, expect } from "vitest";\nimport { formatDate } from "../src/utils";\n\ndescribe("formatDate", () => {\n  it("should format date correctly", () => {\n    const date = new Date("2024-01-01");\n    expect(formatDate(date)).toBe("2024-01-01T00:00:00.000Z");\n  });\n});' }
    ]
  },
  {
    name: 'docs',
    type: 'folder',
    path: '/workspace/docs',
    children: [
      { name: 'API.md', type: 'file', size: '4.5 KB', path: '/workspace/docs/API.md', content: '# API Documentation\n\n## Endpoints\n\n### GET /api/users\nReturns a list of all users.\n\n**Response:**\n```json\n[\n  {\n    "id": "1",\n    "name": "John Doe",\n    "email": "john@example.com"\n  }\n]\n```' }
    ]
  },
  { name: 'README.md', type: 'file', size: '2.3 KB', path: '/workspace/README.md', content: '# My Project\n\nThis is a sample project demonstrating a modern web application.\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n```bash\nnpm start\n```\n\n## License\n\nMIT' },
  { name: 'package.json', type: 'file', size: '1.5 KB', path: '/workspace/package.json', content: '{\n  "name": "my-project",\n  "version": "1.0.0",\n  "description": "A sample project",\n  "main": "dist/index.js",\n  "scripts": {\n    "start": "node dist/index.js",\n    "build": "tsc",\n    "test": "vitest"\n  },\n  "dependencies": {\n    "express": "^4.18.0"\n  },\n  "devDependencies": {\n    "typescript": "^5.0.0",\n    "vitest": "^1.0.0"\n  }\n}' },
  { name: '.gitignore', type: 'file', size: '0.8 KB', path: '/workspace/.gitignore', content: 'node_modules/\ndist/\n.env\n*.log\n.DS_Store' },
  { name: 'tsconfig.json', type: 'file', size: '0.5 KB', path: '/workspace/tsconfig.json', content: '{\n  "compilerOptions": {\n    "target": "ES2020",\n    "module": "commonjs",\n    "outDir": "./dist",\n    "rootDir": "./src",\n    "strict": true,\n    "esModuleInterop": true\n  },\n  "include": ["src/**/*"],\n  "exclude": ["node_modules"]\n}' }
];

const terminalContent = `ubuntu@sandbox:~$ grep -i hypervisor /proc/cpuinfo && echo "---" && cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || echo "DMI product_name not accessible" && echo "---" && cat /proc/cmdline && echo "---" && (dmesg | egrep -i "kvm|firecracker|hypervisor" || echo "dmesg not accessible or no matches") && echo "---" && systemd-detect-virt
---
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx pdpe1gb rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid tsc_known_freq pni pclmulqdq ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch cpuid_fault invpcid_single ssbd ibrs ibpb stibp ibrs_enhanced fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid mpx avx512f avx512dq rdseed adx smap clflushopt clwb avx512cd avx512bw avx512vl xsaveopt xsavec xgetbv1 xsaves arat umip pku ospke avx512_vnni md_clear flush_l1d arch_capabilities
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx pdpe1gb rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid tsc_known_freq pni pclmulqdq ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch cpuid_fault invpcid_single ssbd ibrs ibpb stibp ibrs_enhanced fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid mpx avx512f avx512dq rdseed adx smap clflushopt clwb avx512cd avx512bw avx512vl xsaveopt xsavec xgetbv1 xsaves arat umip pku ospke avx512_vnni md_clear flush_l1d arch_capabilities
---
BOOT_IMAGE=/boot/vmlinuz-6.1.102 root=UUID=xxx ro console=tty1 console=ttyS0 nvme_core.io_timeout=4294967295 panic=-1
---
[    0.000000] Linux version 6.1.102
[    0.000000] Command line: BOOT_IMAGE=/boot/vmlinuz-6.1.102 root=UUID=xxx ro console=tty1 console=ttyS0
[    0.000000] KERNEL supported cpus:
[    0.000000]   Intel GenuineIntel
[    0.000000]   AMD AuthenticAMD
[    0.000000]   Centaur CentaurHauls
[    0.000000] x86/fpu: Supporting XSAVE feature 0x001: 'x87 floating point registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x002: 'SSE registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x004: 'AVX registers'
[    0.000000] x86/fpu: xstate_offset[2]:  576, xstate_sizes[2]:  256
[    0.000000] x86/fpu: Enabled xstate features 0x7, context size is 832 bytes, using 'compacted' format.
[    0.000000] signal: max sigframe size: 1776
[    0.000000] BIOS-provided physical RAM map:
---
kvm

ubuntu@sandbox:~$`;

export default function ComputerPanel({ isOpen, onClose }: ComputerPanelProps) {
  const [activeTab, setActiveTab] = useState<'terminal' | 'browser' | 'files'>('terminal');
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [loadingFile, setLoadingFile] = useState(false);

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const handleFileClick = async (file: FileNode) => {
    if (file.type === 'file') {
      setLoadingFile(true);
      setSelectedFile(null);
      
      // Simulate loading delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setSelectedFile(file);
      setLoadingFile(false);
    }
  };

  const renderFileTree = (nodes: FileNode[], level: number = 0) => {
    return nodes.map((node) => (
      <div key={node.path}>
        <button
          onClick={() => node.type === 'folder' ? toggleFolder(node.path) : handleFileClick(node)}
          className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-[#2a2a2a] transition-colors group text-left"
          style={{ paddingLeft: `${12 + level * 16}px` }}
        >
          {node.type === 'folder' ? (
            <>
              {expandedFolders.has(node.path) ? (
                <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
              )}
              {expandedFolders.has(node.path) ? (
                <FolderOpen className="w-4 h-4 text-blue-400 flex-shrink-0" />
              ) : (
                <Folder className="w-4 h-4 text-blue-400 flex-shrink-0" />
              )}
              <span className="text-gray-300 text-sm">{node.name}</span>
            </>
          ) : (
            <>
              <div className="w-3.5 h-3.5 flex-shrink-0" />
              <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span className="text-gray-300 text-sm flex-1">{node.name}</span>
              <span className="text-gray-600 text-xs">{node.size}</span>
            </>
          )}
        </button>
        
        {node.type === 'folder' && expandedFolders.has(node.path) && node.children && (
          <div>
            {renderFileTree(node.children, level + 1)}
          </div>
        )}
      </div>
    ));
  };

  if (!isOpen) return null;

  return (
    <div 
      className={`h-full bg-[#1e1e1e] border-l border-[#333] flex flex-col animate-fade-in ${
        isExpanded ? 'fixed inset-0 z-50' : ''
      }`}
      style={{ width: isExpanded ? '100%' : '50%', minWidth: '400px' }}
    >
      {/* Panel Header */}
      <div className="h-12 border-b border-[#333] flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="text-white text-sm font-medium">Leon 的电脑</h3>
          <span className="px-2 py-0.5 rounded bg-blue-600/20 text-blue-400 text-xs">
            正在执行指令...
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button 
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors"
          >
            {isExpanded ? (
              <Minimize2 className="w-4 h-4 text-gray-400" />
            ) : (
              <Maximize2 className="w-4 h-4 text-gray-400" />
            )}
          </button>
          <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
            <Copy className="w-4 h-4 text-gray-400" />
          </button>
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-red-600/20 hover:text-red-400 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="h-10 border-b border-[#333] flex items-center px-2 flex-shrink-0">
        <button
          onClick={() => setActiveTab('terminal')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'terminal' 
              ? 'bg-[#2a2a2a] text-white' 
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <Terminal className="w-4 h-4" />
          <span>终端</span>
        </button>
        <button
          onClick={() => setActiveTab('browser')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'browser' 
              ? 'bg-[#2a2a2a] text-white' 
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <Globe className="w-4 h-4" />
          <span>浏览器</span>
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'files' 
              ? 'bg-[#2a2a2a] text-white' 
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>文件</span>
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'terminal' ? (
          <div className="h-full overflow-auto p-4 terminal font-mono text-sm">
            <pre className="whitespace-pre-wrap break-all text-green-400">
              {terminalContent}
            </pre>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-green-400">ubuntu@sandbox:~$</span>
              <span className="w-2 h-4 bg-green-400 animate-pulse" />
            </div>
          </div>
        ) : activeTab === 'browser' ? (
          <div className="h-full flex items-center justify-center bg-[#0d0d0d]">
            <div className="text-center">
              <Globe className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 text-sm">浏览器视图</p>
              <p className="text-gray-600 text-xs mt-1">正在加载页面...</p>
            </div>
          </div>
        ) : (
          <div className="h-full flex bg-[#1a1a1a]">
            {/* Left: File Tree */}
            <div className="w-64 border-r border-[#333] overflow-auto">
              <div className="p-2">
                {/* Current Path */}
                <div className="flex items-center gap-2 mb-2 px-2 text-xs text-gray-500">
                  <span>/workspace</span>
                </div>
                
                {/* File Tree */}
                <div className="space-y-0.5">
                  {renderFileTree(mockFileSystem)}
                </div>
              </div>
            </div>
            
            {/* Right: File Preview */}
            <div className="flex-1 overflow-auto">
              {loadingFile ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
                    <p className="text-gray-400 text-sm">加载文件中...</p>
                  </div>
                </div>
              ) : selectedFile ? (
                <div className="h-full flex flex-col">
                  {/* File Header */}
                  <div className="border-b border-[#333] px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-300 text-sm font-medium">{selectedFile.name}</span>
                    </div>
                    <span className="text-gray-500 text-xs">{selectedFile.path}</span>
                  </div>
                  
                  {/* File Content */}
                  <div className="flex-1 overflow-auto p-4">
                    <pre className="text-gray-300 text-sm font-mono whitespace-pre-wrap">
                      {selectedFile.content}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500 text-sm">选择一个文件查看内容</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="h-1 bg-[#333] flex-shrink-0">
        <div className="h-full bg-blue-500 w-3/4 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_1.5s_infinite]" />
        </div>
      </div>

      {/* Bottom Info */}
      <div className="h-10 border-t border-[#333] flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
            <span className="text-gray-400 text-xs">实时</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-gray-500 text-xs">
          <span>分析硬件与内核日志并报告结论</span>
          <span>2 / 3</span>
        </div>
      </div>
    </div>
  );
}
