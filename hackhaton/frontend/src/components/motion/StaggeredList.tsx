/**
 * StaggeredList (T042).
 *
 * Wraps a list of nodes in a Framer Motion container that fades each item in
 * with a slight stagger. The result page uses this to make catalog items feel
 * unhurried as they appear.
 */
import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface StaggeredListProps {
  children: ReactNode;
  className?: string;
  delayBase?: number;
}

const container = (delayBase: number) => ({
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: delayBase },
  },
});

const item = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.36, ease: [0.16, 1, 0.3, 1] } },
};

export function StaggeredList({
  children,
  className,
  delayBase = 0.05,
}: StaggeredListProps) {
  return (
    <motion.div
      variants={container(delayBase)}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggeredItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div variants={item} className={className}>
      {children}
    </motion.div>
  );
}
