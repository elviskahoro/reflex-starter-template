import { defineRailway, github, project, service } from "railway/iac";
// This repository manages only its own resources in the environment.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "web";
export default defineRailway(() => {
  const web = service("web", {
    source: github("elviskahoro/reflex-starter-template", { branch: "main", checkSuites: false }),
    // Uppercase DOCKERFILE is required; lowercase is not persisted.
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile", watchPatterns: ["Dockerfile", "pyproject.toml", "uv.lock", "web/**", "Caddyfile", "entrypoint.sh"] },
    deploy: { restartPolicyType: "ON_FAILURE", restartPolicyMaxRetries: 5, drainingSeconds: 30 },
    healthcheck: "/ping",
    healthcheckTimeout: 10,
  });

  return project("reflex-starter-template", {
    variables: { managed: false },
    resources: [web],
  });
});
