/**
 * PageTransition (T041).
 *
 * Slide + fade wrapper for wizard steps. Uses Framer Motion's AnimatePresence
 * upstream; this component only exposes the consistent variants.
 */
import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface PageTransitionProps {
  motionKey: string | number;
  direction?: "forward" | "backward";
  children: ReactNode;
  className?: string;
}

const variants = {
  enter: (direction: "forward" | "backward") => ({
    x: direction === "forward" ? 32 : -32,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: "forward" | "backward") => ({
    x: direction === "forward" ? -32 : 32,
    opacity: 0,
  }),
};

export function PageTransition({
  motionKey,
  direction = "forward",
  children,
  className,
}: PageTransitionProps) {
  return (
    <motion.div
      key={motionKey}
      custom={direction}
      variants={variants}
      initial="enter"
      animate="center"
      exit="exit"
      transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
