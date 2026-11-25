(function () {
  const page = document.querySelector(".share");
  const recent = document.getElementById("share-recent");
  if (!page || !recent) {
    return;
  }
  fetch(`/share/s/${encodeURIComponent(page.dataset.token)}.json`)
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (!data) {
        return;
      }
      const when = new Date(data.created).toLocaleDateString();
      recent.innerHTML = `Viewing <strong>${data.title}</strong>, shared ${when}`;
    });
})();
