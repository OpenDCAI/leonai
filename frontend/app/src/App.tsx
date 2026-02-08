import { useState, useCallback } from 'react';
import './App.css';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ChatArea from './components/ChatArea';
import InputBox from './components/InputBox';
import TaskProgress from './components/TaskProgress';
import ComputerPanel from './components/ComputerPanel';
import SearchModal from './components/SearchModal';

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [computerOpen, setComputerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  const toggleComputer = useCallback(() => {
    setComputerOpen(prev => !prev);
  }, []);

  const openComputer = useCallback(() => {
    setComputerOpen(true);
  }, []);

  const closeComputer = useCallback(() => {
    setComputerOpen(false);
  }, []);

  const openSearch = useCallback(() => {
    setSearchOpen(true);
  }, []);

  const closeSearch = useCallback(() => {
    setSearchOpen(false);
  }, []);

  // Keyboard shortcut for search
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setSearchOpen(prev => !prev);
    }
  }, []);

  // Add keyboard listener
  useState(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  return (
    <div className="h-screen w-screen bg-[#1a1a1a] flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar 
        onSearchClick={openSearch}
        collapsed={sidebarCollapsed}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <Header 
          onToggleSidebar={toggleSidebar}
          onToggleComputer={toggleComputer}
          computerOpen={computerOpen}
        />

        {/* Content Area */}
        <div className="flex-1 flex min-h-0">
          {/* Chat Area */}
          <div className={`flex flex-col transition-all duration-300 ${computerOpen ? 'w-1/2' : 'flex-1'}`}>
            <ChatArea onOpenComputer={openComputer} />
            <TaskProgress onOpenComputer={openComputer} />
            <InputBox />
          </div>

          {/* Computer Panel */}
          {computerOpen && (
            <ComputerPanel 
              isOpen={computerOpen}
              onClose={closeComputer}
            />
          )}
        </div>
      </div>

      {/* Search Modal */}
      <SearchModal 
        isOpen={searchOpen}
        onClose={closeSearch}
      />
    </div>
  );
}

export default App;
