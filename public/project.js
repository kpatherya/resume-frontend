const PROJECT_MANIFEST_URL = "/data/project-manifest.json";

function projectElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

function projectAction(action, projectTitle) {
  const link = projectElement("a", "button button-secondary", action.label);
  link.href = action.url;

  if (!action.url.startsWith("#")) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", `${action.label} for ${projectTitle} (opens in a new tab)`);
  }

  return link;
}

function renderList(container, items, ordered = false) {
  const list = projectElement(ordered ? "ol" : "ul", "detail-list");
  items.forEach((item) => list.append(projectElement("li", "", item)));
  container.append(list);
}

function renderProject(project) {
  document.title = `${project.title} | Kausar Patherya`;
  document.querySelector('meta[name="description"]').content = project.summary;
  document.querySelector("#project-eyebrow").textContent = project.eyebrow;
  document.querySelector("#project-status").textContent = project.status;
  document.querySelector("#project-title").textContent = project.title;
  document.querySelector("#project-headline").textContent = project.headline;
  document.querySelector("#project-summary").textContent = project.summary;
  const collaborators = document.querySelector("#project-collaborators");
  if (project.collaborators?.length) {
    collaborators.textContent = `\u{1F44F} Special thanks to my collaborators: ${project.collaborators.join(", ")}`;
    collaborators.hidden = false;
  } else {
    collaborators.remove();
  }
  document.querySelector("#project-problem").textContent = project.problem;
  document.querySelector("#project-contribution").textContent = project.contribution;
  document.querySelector("#project-limitations").textContent = project.limitations;

  const image = document.querySelector("#project-image");
  image.src = project.image.src;
  image.alt = project.image.alt;

  const actions = document.querySelector("#project-actions");
  project.actions.forEach((action) => actions.append(projectAction(action, project.title)));
  if (project.actions.length === 0) actions.remove();

  renderList(document.querySelector("#project-pipeline"), project.pipeline, true);
  renderList(document.querySelector("#project-evidence"), project.evidence);
}

function renderMissingProject() {
  document.title = "Project not found | Kausar Patherya";
  document.querySelector("#project-content").replaceChildren(
    projectElement("h1", "", "Project not found"),
    projectElement("p", "project-summary", "This project is not part of the approved public portfolio."),
  );
}

async function initializeProject() {
  const slug = document.body.dataset.project;

  try {
    const response = await fetch(PROJECT_MANIFEST_URL);
    if (!response.ok) throw new Error(`Manifest request failed: ${response.status}`);
    const manifest = await response.json();
    const project = manifest.projects.find((candidate) => candidate.slug === slug);
    if (!project) return renderMissingProject();
    renderProject(project);
  } catch (error) {
    console.error(error);
    document.querySelector("#project-content").replaceChildren(
      projectElement("p", "load-error", "This project could not be loaded. Please return to the portfolio and try again."),
    );
  }
}

initializeProject();