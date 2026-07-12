import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Disclaimer } from "../Disclaimer";

describe("Disclaimer", () => {
  afterEach(() => cleanup());

  it("renders full disclaimer with 不构成投资建议", () => {
    render(<Disclaimer />);
    expect(screen.getByText(/不构成投资建议/)).toBeInTheDocument();
  });

  it("renders compact disclaimer", () => {
    render(<Disclaimer compact />);
    expect(screen.getByText(/只客观呈现公开数据与榜单/)).toBeInTheDocument();
    expect(screen.getByText(/不推荐个股/)).toBeInTheDocument();
  });

  it("mounts without throwing", () => {
    expect(() => render(<Disclaimer />)).not.toThrow();
  });
});
