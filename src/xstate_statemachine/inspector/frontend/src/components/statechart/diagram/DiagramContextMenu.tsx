// src/components/DiagramContextMenu.tsx
type ContextMenuProps = {
  x: number;
  y: number;
  onClose: () => void;
  onAutoLayout: () => void;
  onFitView: () => void;
};

export const DiagramContextMenu = ({
  x,
  y,
  onClose,
  onAutoLayout,
  onFitView,
}: ContextMenuProps) => {
  return (
    <div
      style={{ left: x, top: y }}
      className="absolute z-50 rounded-md border bg-popover text-popover-foreground shadow-md"
      onMouseLeave={onClose}
    >
      <button
        className="w-full text-left px-3 py-2 hover:bg-muted"
        onClick={() => {
          onClose();
          onAutoLayout();
        }}
      >
        Auto layout
      </button>
      <button
        className="w-full text-left px-3 py-2 hover:bg-muted"
        onClick={() => {
          onClose();
          onFitView();
        }}
      >
        Fit view
      </button>
    </div>
  );
};
