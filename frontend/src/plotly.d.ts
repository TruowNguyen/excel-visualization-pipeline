declare module 'plotly.js-dist-min' {
  const Plotly: {
    react: (element: HTMLElement, data: unknown[], layout: Record<string, unknown>, config?: Record<string, unknown>) => Promise<unknown>;
    restyle: (element: HTMLElement, update: Record<string, unknown>, traces?: number[]) => Promise<unknown>;
    purge: (element: HTMLElement) => void;
  };
  export default Plotly;
}
