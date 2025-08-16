import { cn } from "@/lib/utils";
import React, { CSSProperties } from "react";

export interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  shimmerColor?: string;
  shimmerSize?: string;
  borderRadius?: string;
  shimmerDuration?: string;
  background?: string;
  className?: string;
  children?: React.ReactNode;
}

const ShimmerButton = React.forwardRef<HTMLButtonElement, ShimmerButtonProps>(
  (
    {
      shimmerColor = "#ffffff",
      shimmerSize = "0.1em",
      shimmerDuration = "1.5s",
      borderRadius = "100px",
      background = "rgba(0, 0, 0, 1)",
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        style={
          {
            "--shimmer-color": shimmerColor,
            "--shimmer-size": shimmerSize,
            "--shimmer-duration": shimmerDuration,
            "--background": background,
            borderRadius: borderRadius,
          } as CSSProperties
        }
        className={cn(
          "group relative z-0 flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap border border-white/10 px-6 py-3 text-white [background:var(--background)] [border-radius:var(--border-radius)]",
          "transform-gpu transition-transform duration-300 ease-in-out hover:scale-105",
          className,
        )}
        ref={ref}
        {...props}
      >
        {/* Shimmer */}
        <div className="absolute inset-0 z-0 overflow-hidden rounded-[inherit]">
          <div
            className={cn(
              "absolute inset-0 z-0 h-full w-full animate-[shimmer_var(--shimmer-duration)_infinite] bg-gradient-to-r from-transparent via-transparent to-[var(--shimmer-color)] opacity-0 transition-opacity duration-500 group-hover:opacity-100",
              "[--shimmer-angle:-45deg]",
            )}
          />
        </div>

        {/* Contents */}
        <div className="relative z-10">{children}</div>
      </button>
    );
  },
);

ShimmerButton.displayName = "ShimmerButton";

export default ShimmerButton;
