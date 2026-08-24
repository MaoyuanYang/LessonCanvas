import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders the product entry", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "LessonCanvas" })).toBeInTheDocument();
    expect(screen.getByText(/单元备课工作台/)).toBeInTheDocument();
  });
});
