"use client";

interface FooterProps {
  generatedTime: string;
}

export default function Footer({ generatedTime }: FooterProps) {
  return (
    <div className="footer">
      <div className="footer-content">
        <div className="footer-sources">
          Data from NCAA, MLB Stats API, Chadwick Bureau
        </div>
        <div>Generated {generatedTime}</div>
      </div>
    </div>
  );
}
