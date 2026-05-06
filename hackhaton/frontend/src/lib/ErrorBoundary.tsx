import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface to console — no analytics in v1 (FR-013).
    console.error("UI error boundary caught:", error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div className="grid min-h-dvh place-items-center px-4">
          <Card className="glass max-w-md">
            <CardContent className="space-y-4 p-6 text-sm">
              <div className="text-base font-semibold">
                Something went wrong on this screen.
              </div>
              <p className="text-muted-foreground">
                Try going back, or reload the app. If it keeps happening, check
                the inventory update.
              </p>
              <Button onClick={this.reset} variant="default">
                Try again
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}
