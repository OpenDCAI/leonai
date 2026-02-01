'use client';

interface ObjectProps {
  name: string;
  emoji: string;
  isHighlighted: boolean;
  position: 'left' | 'center' | 'right';
}

export default function ObjectItem({ name, emoji, isHighlighted, position }: ObjectProps) {
  const positionClasses = {
    left: 'left-8',
    center: 'left-1/2 -translate-x-1/2',
    right: 'right-8',
  };

  return (
    <div
      className={`absolute bottom-8 ${positionClasses[position]} flex flex-col items-center transition-all duration-300 ${
        isHighlighted ? 'scale-125 -translate-y-4' : ''
      }`}
    >
      {/* Object */}
      <div
        className={`text-6xl transition-all duration-300 ${
          isHighlighted ? 'animate-bounce drop-shadow-[0_0_20px_rgba(255,215,0,0.8)]' : ''
        }`}
      >
        {emoji}
      </div>

      {/* Label */}
      <div
        className={`mt-2 px-3 py-1 rounded-full text-sm font-medium transition-all duration-300 ${
          isHighlighted
            ? 'bg-yellow-400 text-yellow-900 shadow-lg'
            : 'bg-gray-200 text-gray-600'
        }`}
      >
        {name}
      </div>

      {/* Highlight ring */}
      {isHighlighted && (
        <div className="absolute -inset-4 border-4 border-yellow-400 rounded-full animate-ping opacity-50" />
      )}
    </div>
  );
}
