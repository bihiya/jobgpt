# Folder Structure

```
jobpilot-ai/
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── api/v1/{auth,users,jobs,applications,companies,portals,reports,automation,scheduler,settings}/
│   │   ├── automation/{base,portals,pages}/
│   │   ├── consumers/
│   │   ├── core/
│   │   ├── db/
│   │   ├── dependencies/
│   │   ├── events/
│   │   ├── middleware/
│   │   ├── models/
│   │   ├── producers/
│   │   ├── repository/
│   │   ├── scheduler/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── workers/
│   │   └── main.py
│   ├── tests/{unit,integration,e2e}/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── store/{slices}/   # Redux Toolkit (JavaScript)
│   │   ├── theme/
│   │   ├── types/
│   │   └── utils/
│   ├── tests/
│   ├── Dockerfile
│   └── package.json
├── e2e/
├── k8s/
├── monitoring/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```
