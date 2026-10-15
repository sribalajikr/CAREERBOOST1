"""Generate a sample student-resume PDF for testing the analysis endpoint."""
import zlib

LINES = [
    "RAHUL SHARMA",
    "Email: rahul.sharma@example.com | Phone: +91 98765 43210",
    "LinkedIn: linkedin.com/in/rahulsharma | GitHub: github.com/rahulsharma",
    "",
    "OBJECTIVE",
    "Motivated computer science student seeking a software developer internship.",
    "",
    "EDUCATION",
    "B.Tech Computer Science, Sunrise Institute of Technology (2023-2027)",
    "CGPA: 8.4/10",
    "",
    "SKILLS",
    "Programming: Python, Java, C++, JavaScript",
    "Web: HTML, CSS, React, Node.js",
    "Databases: SQL, MySQL, MongoDB",
    "Tools: Git, GitHub, Docker, Linux, REST API",
    "",
    "PROJECTS",
    "E-Commerce Website - Built a full stack web app with React and Node.js",
    "- Designed REST APIs with JWT authentication, reduced page load by 35%",
    "- Implemented cart and payment flow used by 50+ test users",
    "Student Attendance System - Python desktop application with MySQL",
    "- Automated attendance tracking, saving 5 hours per week",
    "",
    "CERTIFICATIONS",
    "Google Cloud Fundamentals, AWS Cloud Practitioner (in progress)",
    "",
    "ACHIEVEMENTS",
    "Winner, college hackathon 2025. Solved 200+ DSA problems on LeetCode.",
    "",
    "EXPERIENCE",
    "Web Development Intern, TechStart Solutions (Jun-Jul 2025)",
    "- Developed reusable UI components, improved delivery speed by 20%",
]


def _escape(t: str) -> str:
    return t.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def build_pdf() -> bytes:
    content = ["BT /F1 11 Tf 14 TL 50 780 Td"]
    for line in LINES:
        content.append(f"({_escape(line)}) Tj T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(out)


if __name__ == "__main__":
    with open("sample_resume.pdf", "wb") as f:
        f.write(build_pdf())
    print("sample_resume.pdf written")
