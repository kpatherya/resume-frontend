const MANIFEST_URL = "/data/project-manifest.json";

function createElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

function createAction(action, projectTitle, className = "action-link") {
  const link = createElement("a", className, action.label);
  link.href = action.url;

  if (action.url.startsWith("http")) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", `${action.label} for ${projectTitle} (opens in a new tab)`);
  }

  return link;
}

function renderHero(site) {
  document.querySelector("#hero-heading").textContent = site.headline;
  document.querySelector("#hero-bio").textContent = site.bio;

  document.querySelector("#hero-actions").append(
    createAction(site.primaryAction, site.name, "profile-link"),
    createAction(site.secondaryAction, site.name, "profile-link"),
  );

  const profileActions = document.querySelector("#profile-actions");
  site.profileActions.forEach((action) => {
    const heroLink = createAction(action, site.name, "profile-link");
    document.querySelector("#hero-actions").append(heroLink);
    profileActions.prepend(createAction(action, site.name));
  });
}

function renderThemes(themes) {
  const container = document.querySelector("#research-themes");
  themes.forEach((theme, index) => {
    const article = createElement("article", "theme-item");
    article.append(
      createElement("span", "theme-number", String(index + 1).padStart(2, "0")),
      createElement("h3", "", theme.title),
      createElement("p", "", theme.description),
    );
    container.append(article);
  });
}

function renderProjectCard(project) {
  const article = createElement("article", `project-card project-card-${project.tier}`);
  const projectUrl = `/projects/${project.slug}/index.html`;
  const mediaLink = createElement("a", "project-media");
  mediaLink.href = projectUrl;
  mediaLink.setAttribute("aria-label", `View ${project.title} project details`);

  const image = createElement("img");
  image.src = project.image.src;
  image.alt = project.image.alt;
  image.loading = "lazy";
  mediaLink.append(image);

  const body = createElement("div", "project-card-body");
  const meta = createElement("div", "project-meta");
  meta.append(
    createElement("span", "project-eyebrow", project.eyebrow),
    createElement("span", "status-tag", project.status),
  );

  const heading = createElement("h3");
  const titleLink = createElement("a", "project-title-link", project.title);
  titleLink.href = projectUrl;
  heading.append(titleLink);

  body.append(
    meta,
    heading,
    createElement("p", "project-headline", project.headline),
    createElement("p", "project-summary", project.summary),
  );

  const actions = createElement("div", "project-actions");
  actions.append(createAction({ label: "View project", url: projectUrl }, project.title, "action-link action-link-primary"));
  project.actions.forEach((action) => actions.append(createAction(action, project.title)));
  body.append(actions);
  article.append(mediaLink, body);
  return article;
}

function renderProjects(projects) {
  const featured = document.querySelector("#featured-projects");
  const supporting = document.querySelector("#supporting-projects");

  projects.forEach((project) => {
    const destination = project.tier === "featured" ? featured : supporting;
    destination.append(renderProjectCard(project));
  });
}

function renderLoadError() {
  const message = createElement("p", "load-error", "The project catalog could not be loaded. Please refresh the page.");
  document.querySelector("#featured-projects").replaceChildren(message);
}

async function initializePortfolio() {
  try {
    const response = await fetch(MANIFEST_URL);
    if (!response.ok) throw new Error(`Manifest request failed: ${response.status}`);
    const manifest = await response.json();
    renderHero(manifest.site);
    renderThemes(manifest.researchThemes);
    renderProjects(manifest.projects);
  } catch (error) {
    console.error(error);
    renderLoadError();
  }
}

initializePortfolio();