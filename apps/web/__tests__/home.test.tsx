import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@clerk/nextjs", () => ({
  SignInButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  UserButton: () => null,
  useUser: () => ({ isSignedIn: false }),
}));

import PublicEntryPage from "../app/(public)/page";

describe("PublicEntryPage", () => {
  it("renders the product entry with privacy boundary", () => {
    render(<PublicEntryPage />);
    expect(screen.getByRole("heading", { name: "LessonCanvas" })).toBeInTheDocument();
    expect(screen.getByText(/单元备课工作台/)).toBeInTheDocument();
    expect(screen.getByText(/仅属于你的工作区/)).toBeInTheDocument();
  });
});
