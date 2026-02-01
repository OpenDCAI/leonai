'use client';

import { useEffect, useState, useCallback } from 'react';
import Cat from '@/components/Cat';
import ObjectItem from '@/components/Object';

const objects = [
  { name: '萝卜', emoji: '🥕', position: 'left' as const },
  { name: '纸巾', emoji: '🧻', position: 'center' as const },
  { name: '米奇', emoji: '🐭', position: 'right' as const },
];

export default function Home() {
  const [currentTarget, setCurrentTarget] = useState<string | null>(null);
  const [lastTimestamp, setLastTimestamp] = useState<number>(0);

  const pollState = useCallback(async () => {
    try {
      const response = await fetch('/api/point', {
        method: 'GET',
        cache: 'no-store',
      });
      const data = await response.json();

      if (data.timestamp > lastTimestamp) {
        setCurrentTarget(data.target);
        setLastTimestamp(data.timestamp);
      }
    } catch (error) {
      console.error('Failed to poll state:', error);
    }
  }, [lastTimestamp]);

  useEffect(() => {
    // Poll every 500ms
    const interval = setInterval(pollState, 500);
    return () => clearInterval(interval);
  }, [pollState]);

  // Manual trigger for testing
  const handleManualPoint = async (target: string) => {
    try {
      await fetch('/api/point', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target }),
      });
      // Immediately update local state
      setCurrentTarget(target);
      setLastTimestamp(Date.now());
    } catch (error) {
      console.error('Failed to point:', error);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-sky-200 to-green-200 flex flex-col items-center justify-center relative overflow-hidden">
      {/* Title */}
      <h1 className="absolute top-8 text-4xl font-bold text-gray-800 drop-shadow-lg">
        🐱 小猫指物 🐱
      </h1>

      {/* Subtitle */}
      <p className="absolute top-20 text-gray-600">
        对 Leon 说出物品名称，小猫会指向它！
      </p>

      {/* Cat in the center-top area */}
      <div className="absolute top-32">
        <Cat target={currentTarget} />
      </div>

      {/* Objects at the bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-green-300 to-transparent">
        {objects.map((obj) => (
          <ObjectItem
            key={obj.name}
            name={obj.name}
            emoji={obj.emoji}
            isHighlighted={currentTarget === obj.name}
            position={obj.position}
          />
        ))}
      </div>

      {/* Manual test buttons */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-4">
        {objects.map((obj) => (
          <button
            key={obj.name}
            onClick={() => handleManualPoint(obj.name)}
            className="px-4 py-2 bg-white/80 hover:bg-white rounded-lg shadow-md transition-all hover:scale-105 active:scale-95"
          >
            {obj.emoji} {obj.name}
          </button>
        ))}
      </div>

      {/* Status indicator */}
      <div className="absolute top-4 right-4 flex items-center gap-2 bg-white/80 px-3 py-1 rounded-full text-sm">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        <span>监听中...</span>
      </div>
    </main>
  );
}
