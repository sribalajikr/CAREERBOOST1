"""Career catalog — skill requirements, descriptions and learning paths.

This is the knowledge base used by the rule-based career matching engine.
A real AI provider can augment this, but the app must work with it alone.
"""

CAREERS = {
    "Software Developer": {
        "description": "Builds reliable software products end to end — from writing clean code to shipping features users love.",
        "core": ["Programming Fundamentals", "DSA", "OOP", "Git", "SQL"],
        "nice": ["APIs", "Testing", "Linux", "Python", "Java", "C++"],
        "salary_hint": "₹4–12 LPA (entry, India)",
        "learning_path": ["Master one language deeply", "Learn OOP + DSA", "Practice SQL", "Build 3 solid projects", "Solve 150+ coding problems", "Prepare resume + interviews"],
    },
    "Full Stack Developer": {
        "description": "Handles both the frontend users see and the backend that powers it — a complete web product builder.",
        "core": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "Git", "APIs"],
        "nice": ["TypeScript", "MongoDB", "Tailwind", "Express", "Next.js", "Docker"],
        "salary_hint": "₹5–14 LPA (entry, India)",
        "learning_path": ["HTML/CSS/JS basics", "React fundamentals", "Node + Express APIs", "Databases (SQL/Mongo)", "Full-stack capstone project", "Deploy your app live"],
    },
    "Backend Developer": {
        "description": "Designs the server-side logic, databases and APIs that make applications work behind the scenes.",
        "core": ["Data Structures", "OOP", "SQL", "APIs", "Git", "Python"],
        "nice": ["Java", "Node.js", "Docker", "Redis", "System Design", "Linux"],
        "salary_hint": "₹5–15 LPA (entry, India)",
        "learning_path": ["Pick a backend language", "REST API design", "Relational databases", "Authentication & security basics", "Caching & message queues", "Scale a real project"],
    },
    "Frontend Developer": {
        "description": "Creates beautiful, fast and accessible user interfaces using modern web technologies.",
        "core": ["HTML", "CSS", "JavaScript", "React", "Git"],
        "nice": ["TypeScript", "Tailwind", "Redux", "Next.js", "Accessibility", "Testing"],
        "salary_hint": "₹4–12 LPA (entry, India)",
        "learning_path": ["HTML + CSS layout mastery", "JavaScript ES6+", "React components & hooks", "State management", "Responsive design practice", "Portfolio of 3 UI projects"],
    },
    "Data Analyst": {
        "description": "Turns raw data into clear insights and dashboards that help teams make better decisions.",
        "core": ["SQL", "Python", "Statistics", "Excel", "Data Visualization"],
        "nice": ["Power BI", "Tableau", "Pandas", "Communication", "R"],
        "salary_hint": "₹4–10 LPA (entry, India)",
        "learning_path": ["Excel + SQL foundations", "Python (Pandas, NumPy)", "Statistics essentials", "Visualization tools (Power BI/Tableau)", "Build 2 analysis case studies", "Storytelling with data"],
    },
    "Data Scientist": {
        "description": "Combines statistics, programming and machine learning to predict outcomes and solve business problems.",
        "core": ["Python", "Statistics", "Machine Learning", "SQL", "Pandas"],
        "nice": ["Scikit-learn", "Deep Learning", "Mathematics", "Data Visualization", "NLP"],
        "salary_hint": "₹6–18 LPA (entry, India)",
        "learning_path": ["Python + Pandas", "Probability & statistics", "ML algorithms (scikit-learn)", "Model evaluation & tuning", "Kaggle competitions", "End-to-end ML project"],
    },
    "AI/ML Engineer": {
        "description": "Builds and deploys intelligent systems — from training models to putting them into production apps.",
        "core": ["Python", "Machine Learning", "Deep Learning", "Mathematics", "Data Structures"],
        "nice": ["PyTorch", "TensorFlow", "NLP", "Computer Vision", "MLOps", "Docker"],
        "salary_hint": "₹6–20 LPA (entry, India)",
        "learning_path": ["Python + NumPy", "Linear algebra & calculus basics", "Core ML algorithms", "Deep learning (PyTorch)", "Build & deploy an AI project", "Learn MLOps basics"],
    },
    "Cloud Engineer": {
        "description": "Designs and manages scalable infrastructure on cloud platforms like AWS, Azure or GCP.",
        "core": ["Linux", "Networking", "Cloud Platforms", "Python", "Docker"],
        "nice": ["AWS", "Terraform", "Kubernetes", "CI/CD", "Bash", "Security"],
        "salary_hint": "₹5–14 LPA (entry, India)",
        "learning_path": ["Linux fundamentals", "Networking basics", "One cloud platform (AWS free tier)", "Docker & containers", "Infrastructure as Code (Terraform)", "AWS Cloud Practitioner cert"],
    },
    "Cybersecurity Analyst": {
        "description": "Protects systems and data by finding vulnerabilities, monitoring threats and responding to attacks.",
        "core": ["Networking", "Linux", "Security Fundamentals", "Python", "Operating Systems"],
        "nice": ["Wireshark", "Burp Suite", "Cryptography", "SIEM", "Ethical Hacking"],
        "salary_hint": "₹4–12 LPA (entry, India)",
        "learning_path": ["Networking (TCP/IP, DNS, HTTP)", "Linux administration", "Security fundamentals (CIA triad)", "TryHackMe / HackTheBox labs", "Web vulnerabilities (OWASP Top 10)", "CompTIA Security+ path"],
    },
    "DevOps Engineer": {
        "description": "Bridges development and operations — automating builds, deployments and infrastructure.",
        "core": ["Linux", "Git", "Docker", "CI/CD", "Python", "Cloud Platforms"],
        "nice": ["Kubernetes", "Jenkins", "Terraform", "Monitoring", "Bash", "Ansible"],
        "salary_hint": "₹5–16 LPA (entry, India)",
        "learning_path": ["Linux + shell scripting", "Git workflows", "Docker containers", "CI/CD pipelines (GitHub Actions)", "Kubernetes basics", "Automate deployment of a real app"],
    },
    "QA / Automation Engineer": {
        "description": "Guards software quality by writing automated tests and catching bugs before users do.",
        "core": ["Testing", "Selenium", "Python", "Java", "Git"],
        "nice": ["Playwright", "API Testing", "Postman", "Cypress", "Agile", "Jenkins"],
        "salary_hint": "₹4–10 LPA (entry, India)",
        "learning_path": ["Manual testing basics", "Java/Python for testers", "Selenium WebDriver", "API testing (Postman/RestAssured)", "Test frameworks (TestNG/PyTest)", "Build an automation suite"],
    },
}

# synonyms so resume text and skills map onto catalog skills
SKILL_ALIASES = {
    "cpp": "C++", "c plus plus": "C++", "golang": "Go", "js": "JavaScript",
    "ts": "TypeScript", "ml": "Machine Learning", "ai": "AI",
    "dl": "Deep Learning", "postgres": "PostgreSQL", "postgres sql": "PostgreSQL",
    "my sql": "MySQL", "node": "Node.js", "nodejs": "Node.js",
    "rest": "APIs", "restful": "APIs", "api": "APIs", "rest api": "APIs",
    "github": "Git", "excel": "Excel", "powerbi": "Power BI", "power bi": "Power BI",
    "aws": "AWS", "gcp": "Google Cloud", "azure": "Azure", "k8s": "Kubernetes",
    "selenium": "Selenium", "pytorch": "PyTorch", "tensorflow": "TensorFlow",
    "sklearn": "Scikit-learn", "scikit": "Scikit-learn", "oop": "OOP",
    "data structures": "DSA", "data structure": "DSA", "dsa": "DSA",
    "algorithms": "DSA", "problem solving": "DSA", "html5": "HTML",
    "css3": "CSS", "reactjs": "React", "react.js": "React",
    "big data": "Data Analytics", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning", "data visualization": "Data Visualization",
    "dashboards": "Data Visualization", "cloud": "Cloud Platforms",
    "cloud computing": "Cloud Platforms", "cyber security": "Security Fundamentals",
    "ethical hacking": "Ethical Hacking", "penetration testing": "Ethical Hacking",
    "shell scripting": "Bash", "bash": "Bash", "sql queries": "SQL",
    "mysql": "SQL", "sqlite": "SQL", "database": "SQL", "dbms": "SQL",
    "mongodb": "MongoDB", "nosql": "MongoDB", "devops": "CI/CD",
    "automation": "Testing", "manual testing": "Testing",
}

# Conceptual catalog skills count as "had" when the user knows any concrete skill below.
SKILL_EQUIVALENTS = {
    "Programming Fundamentals": ["Python", "Java", "C++", "C", "JavaScript", "C#", "Go", "Kotlin", "PHP"],
    "APIs": ["Node.js", "Express", "FastAPI", "Django", "Flask", "Spring", "REST"],
    "Statistics": ["Probability", "Mathematics", "R"],
    "Data Visualization": ["Power BI", "Tableau", "Matplotlib", "Seaborn"],
    "Cloud Platforms": ["AWS", "Azure", "Google Cloud"],
    "Testing": ["Selenium", "Playwright", "Cypress", "PyTest", "TestNG"],
    "Security Fundamentals": ["Ethical Hacking", "Cryptography", "OWASP"],
    "Operating Systems": ["Linux"],
    "CI/CD": ["Jenkins", "GitHub Actions", "GitHub"],
    "Deep Learning": ["PyTorch", "TensorFlow"],
    "Machine Learning": ["Scikit-learn"],
    "DSA": ["Algorithms", "Data Structures"],
    "Excel": ["Google Sheets"],
    "Data Structures": ["DSA", "Algorithms"],
    "OOP": ["Java", "Python", "C++", "C#"],
    "Git": ["GitHub", "GitLab"],
    "Networking": ["TCP/IP", "DNS"],
}

# keywords that hint at interest areas for recommendation "why" reasoning
INTEREST_KEYWORDS = {
    "Data Analyst": ["data", "analytics", "statistics", "dashboards", "reports", "visualization", "insights"],
    "Data Scientist": ["data", "analytics", "statistics", "machine learning", "prediction", "modeling"],
    "AI/ML Engineer": ["ai", "machine learning", "deep learning", "neural", "chatbot", "ml", "llm", "models"],
    "Full Stack Developer": ["web", "full stack", "applications", "websites", "mern", "product"],
    "Backend Developer": ["backend", "server", "api", "database", "microservices", "logic"],
    "Frontend Developer": ["ui", "ux", "frontend", "design", "web", "interface", "responsive"],
    "Cloud Engineer": ["cloud", "aws", "azure", "gcp", "infrastructure", "deployment"],
    "Cybersecurity Analyst": ["security", "hacking", "cyber", "network", "penetration", "cryptography"],
    "DevOps Engineer": ["devops", "deployment", "docker", "ci/cd", "automation", "infrastructure"],
    "QA / Automation Engineer": ["testing", "qa", "quality", "automation", "bugs", "selenium"],
    "Software Developer": ["software", "coding", "programming", "development", "java", "python", "dsa"],
}

# Preferred-career synonyms -> canonical catalog key
PREFERRED_ALIASES = {
    "sde": "Software Developer", "sde-1": "Software Developer",
    "software engineer": "Software Developer", "developer": "Software Developer",
    "programmer": "Software Developer", "web developer": "Full Stack Developer",
    "mern developer": "Full Stack Developer", "fullstack": "Full Stack Developer",
    "full-stack developer": "Full Stack Developer",
    "back end developer": "Backend Developer", "backend engineer": "Backend Developer",
    "front end developer": "Frontend Developer", "frontend engineer": "Frontend Developer",
    "business analyst": "Data Analyst", "data analytics": "Data Analyst",
    "ai engineer": "AI/ML Engineer", "machine learning engineer": "AI/ML Engineer",
    "ml engineer": "AI/ML Engineer", "data engineer": "Data Scientist",
    "cloud architect": "Cloud Engineer", "security analyst": "Cybersecurity Analyst",
    "cyber security": "Cybersecurity Analyst", "sre": "DevOps Engineer",
    "site reliability engineer": "DevOps Engineer", "test engineer": "QA / Automation Engineer",
    "qa engineer": "QA / Automation Engineer", "sdet": "QA / Automation Engineer",
}
