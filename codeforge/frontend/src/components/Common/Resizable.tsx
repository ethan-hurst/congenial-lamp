/**
 * Resizable Panel Components
 */
import React, { useState, useRef, useEffect, ReactNode } from 'react';
import clsx from 'clsx';

interface ResizablePanelGroupProps {
  direction: 'horizontal' | 'vertical';
  className?: string;
  children: ReactNode;
}

interface ResizablePanelProps {
  defaultSize?: number;
  minSize?: number;
  maxSize?: number;
  className?: string;
  children: ReactNode;
}

interface ResizableHandleProps {
  className?: string;
}

// Context for sharing state between panels
const ResizableContext = React.createContext<{
  direction: 'horizontal' | 'vertical';
  panels: Map<string, { size: number; minSize: number; maxSize: number }>;
  registerPanel: (id: string, config: { size: number; minSize: number; maxSize: number }) => void;
  updatePanelSize: (id: string, size: number) => void;
} | null>(null);

export const ResizablePanelGroup: React.FC<ResizablePanelGroupProps> = ({
  direction,
  className,
  children,
}) => {
  const [panels] = useState(new Map());

  const registerPanel = (id: string, config: { size: number; minSize: number; maxSize: number }) => {
    panels.set(id, config);
  };

  const updatePanelSize = (id: string, size: number) => {
    const panel = panels.get(id);
    if (panel) {
      panel.size = size;
    }
  };

  return (
    <ResizableContext.Provider value={{ direction, panels, registerPanel, updatePanelSize }}>
      <div
        className={clsx(
          'flex h-full w-full',
          direction === 'horizontal' ? 'flex-row' : 'flex-col',
          className
        )}
      >
        {children}
      </div>
    </ResizableContext.Provider>
  );
};

export const ResizablePanel: React.FC<ResizablePanelProps> = ({
  defaultSize = 50,
  minSize = 10,
  maxSize = 90,
  className,
  children,
}) => {
  const context = React.useContext(ResizableContext);
  const [size, setSize] = useState(defaultSize);
  const panelId = useRef(`panel-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (context) {
      context.registerPanel(panelId.current, { size, minSize, maxSize });
    }
  }, [context, size, minSize, maxSize]);

  const style: React.CSSProperties = context
    ? context.direction === 'horizontal'
      ? { width: `${size}%`, minWidth: `${minSize}%`, maxWidth: `${maxSize}%` }
      : { height: `${size}%`, minHeight: `${minSize}%`, maxHeight: `${maxSize}%` }
    : {};

  return (
    <div className={clsx('overflow-hidden', className)} style={style}>
      {children}
    </div>
  );
};

export const ResizableHandle: React.FC<ResizableHandleProps> = ({ className }) => {
  const context = React.useContext(ResizableContext);
  const [isDragging, setIsDragging] = useState(false);
  const handleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!context || !handleRef.current) return;

    let startPos = 0;
    let startSize = 0;
    let panelElement: HTMLElement | null = null;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      
      panelElement = handleRef.current?.previousElementSibling as HTMLElement;
      if (!panelElement) return;

      startPos = context.direction === 'horizontal' ? e.clientX : e.clientY;
      const rect = panelElement.getBoundingClientRect();
      startSize = context.direction === 'horizontal' ? rect.width : rect.height;

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!panelElement || !context) return;

      const currentPos = context.direction === 'horizontal' ? e.clientX : e.clientY;
      const diff = currentPos - startPos;
      const parentRect = panelElement.parentElement?.getBoundingClientRect();
      
      if (!parentRect) return;

      const parentSize = context.direction === 'horizontal' ? parentRect.width : parentRect.height;
      const newSize = ((startSize + diff) / parentSize) * 100;

      // Apply size constraints
      const clampedSize = Math.max(10, Math.min(90, newSize));
      
      if (context.direction === 'horizontal') {
        panelElement.style.width = `${clampedSize}%`;
      } else {
        panelElement.style.height = `${clampedSize}%`;
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    handleRef.current.addEventListener('mousedown', handleMouseDown);

    return () => {
      handleRef.current?.removeEventListener('mousedown', handleMouseDown);
    };
  }, [context]);

  if (!context) return null;

  return (
    <div
      ref={handleRef}
      className={clsx(
        'relative group',
        context.direction === 'horizontal'
          ? 'w-1 h-full cursor-col-resize'
          : 'h-1 w-full cursor-row-resize',
        isDragging && 'opacity-100',
        className
      )}
    >
      <div
        className={clsx(
          'absolute bg-border transition-colors',
          context.direction === 'horizontal'
            ? 'w-1 h-full hover:bg-primary group-active:bg-primary'
            : 'h-1 w-full hover:bg-primary group-active:bg-primary'
        )}
      />
    </div>
  );
};