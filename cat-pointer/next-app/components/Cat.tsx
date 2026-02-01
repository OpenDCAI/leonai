'use client';

import { useEffect, useState } from 'react';

interface CatProps {
  target: string | null;
}

const targetAngles: Record<string, number> = {
  '萝卜': -45,  // Point left
  '纸巾': 0,    // Point center
  '米奇': 45,   // Point right
};

export default function Cat({ target }: CatProps) {
  const [rotation, setRotation] = useState(0);
  const [isPointing, setIsPointing] = useState(false);

  useEffect(() => {
    if (target && target in targetAngles) {
      setIsPointing(true);
      setRotation(targetAngles[target]);

      // Reset after animation
      const timer = setTimeout(() => {
        setIsPointing(false);
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [target]);

  return (
    <div className="relative flex flex-col items-center">
      {/* Cat body */}
      <div className="relative w-32 h-32">
        {/* Cat face */}
        <div className="absolute inset-0 bg-orange-300 rounded-full border-4 border-orange-400 flex items-center justify-center">
          {/* Ears */}
          <div className="absolute -top-4 -left-2 w-0 h-0 border-l-[16px] border-r-[16px] border-b-[24px] border-l-transparent border-r-transparent border-b-orange-300" />
          <div className="absolute -top-4 -right-2 w-0 h-0 border-l-[16px] border-r-[16px] border-b-[24px] border-l-transparent border-r-transparent border-b-orange-300" />

          {/* Inner ears */}
          <div className="absolute -top-2 left-1 w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-pink-200" />
          <div className="absolute -top-2 right-1 w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-pink-200" />

          {/* Eyes */}
          <div className="absolute top-8 left-6 w-4 h-4 bg-black rounded-full">
            <div className="absolute top-0.5 left-0.5 w-1.5 h-1.5 bg-white rounded-full" />
          </div>
          <div className="absolute top-8 right-6 w-4 h-4 bg-black rounded-full">
            <div className="absolute top-0.5 left-0.5 w-1.5 h-1.5 bg-white rounded-full" />
          </div>

          {/* Nose */}
          <div className="absolute top-14 left-1/2 -translate-x-1/2 w-3 h-2 bg-pink-400 rounded-full" />

          {/* Mouth */}
          <div className="absolute top-16 left-1/2 -translate-x-1/2 text-xs">ω</div>

          {/* Whiskers */}
          <div className="absolute top-14 left-2 w-6 h-0.5 bg-gray-600 -rotate-12" />
          <div className="absolute top-15 left-2 w-6 h-0.5 bg-gray-600" />
          <div className="absolute top-14 right-2 w-6 h-0.5 bg-gray-600 rotate-12" />
          <div className="absolute top-15 right-2 w-6 h-0.5 bg-gray-600" />
        </div>
      </div>

      {/* Pointing arm */}
      <div
        className="absolute top-24 left-1/2 origin-top transition-transform duration-500 ease-out"
        style={{
          transform: `translateX(-50%) rotate(${rotation}deg)`,
        }}
      >
        {/* Arm */}
        <div className={`w-4 h-20 bg-orange-300 rounded-full border-2 border-orange-400 ${isPointing ? 'animate-pulse' : ''}`}>
          {/* Paw */}
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-6 h-4 bg-orange-200 rounded-full border-2 border-orange-300">
            {/* Paw pads */}
            <div className="absolute bottom-0.5 left-1 w-1 h-1 bg-pink-300 rounded-full" />
            <div className="absolute bottom-0.5 right-1 w-1 h-1 bg-pink-300 rounded-full" />
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-pink-300 rounded-full" />
          </div>
        </div>
      </div>

      {/* Speech bubble */}
      {isPointing && target && (
        <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-white px-4 py-2 rounded-xl shadow-lg border-2 border-gray-200 animate-bounce">
          <span className="text-lg font-bold">喵~ {target}!</span>
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-white" />
        </div>
      )}
    </div>
  );
}
