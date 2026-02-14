import React from 'react';
import { clsx } from 'clsx';

export default function SugarLogo({ className = "w-8 h-8" }) {
  return (
    <div className={clsx("grid grid-cols-2 gap-1", className)}>
      <div className="col-span-2 justify-self-center w-[80%] h-[80%] bg-gradient-to-br from-sugar-300 to-sugar-400 rounded-sm shadow-lg shadow-sugar-500/20 translate-y-1"></div>
      <div className="w-full h-full bg-gradient-to-br from-sugar-400 to-sugar-500 rounded-sm shadow-lg shadow-sugar-500/20"></div>
      <div className="w-full h-full bg-gradient-to-br from-sugar-500 to-sugar-600 rounded-sm shadow-lg shadow-sugar-500/20"></div>
    </div>
  );
}
