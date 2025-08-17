//  src/xstate_statemachine/inspector/frontend/src/components/magicui/dock.tsx

"use client";

import { cn } from "@/lib/utils";
// FIX: Split the import into two lines for wider compatibility
import { cva } from "class-variance-authority";
import type { VariantProps } from "class-variance-authority";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import React, { useRef } from "react";

export interface DockProps extends VariantProps<typeof dockVariants> {
  className?: string;
  children: React.ReactNode;
  direction?: "top" | "bottom" | "left" | "right";
}

const dockVariants = cva(
  "flex h-full w-max items-end gap-2 rounded-lg p-2 transition-all duration-300 ease-out",
);

const Dock = React.forwardRef<HTMLDivElement, DockProps>(
  ({ className, children, ...props }, ref) => {
    const mouseX = useMotionValue(Infinity);

    return (
      <motion.div
        ref={ref}
        onMouseMove={(e) => mouseX.set(e.pageX)}
        onMouseLeave={() => mouseX.set(Infinity)}
        {...props}
        className={cn(dockVariants({ className }), "z-50")}
      >
        {React.Children.map(children, (child) =>
          React.cloneElement(child as React.ReactElement<any>, {
            mouseX: mouseX,
          }),
        )}
      </motion.div>
    );
  },
);

Dock.displayName = "Dock";

export interface DockIconProps {
  mouseX?: any;
  children?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

const DockIcon = ({ mouseX, className, children, ...props }: DockIconProps) => {
  const ref = useRef<HTMLDivElement>(null);

  const distance = useTransform(mouseX, (val: number) => {
    const bounds = ref.current?.getBoundingClientRect() ?? { x: 0, width: 0 };
    return val - bounds.x - bounds.width / 2;
  });

  const widthSync = useTransform(distance, [-150, 0, 150], [40, 80, 40]);
  const width = useSpring(widthSync, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  });

  return (
    <motion.div
      ref={ref}
      style={{ width }}
      className={cn(
        "flex aspect-square items-center justify-center rounded-full bg-neutral-100/50 dark:bg-neutral-800/50",
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
};

DockIcon.displayName = "DockIcon";

export { Dock, DockIcon };
