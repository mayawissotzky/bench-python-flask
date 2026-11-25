(function () {
  const section = document.getElementById("comments");
  if (!section) return;
  const expenseId = section.dataset.expenseId;
  const userId = Number(section.dataset.userId);
  const list = section.querySelector(".comments");
  const form = section.querySelector(".comment-form");

  function render(comment) {
    const li = document.createElement("li");
    li.id = `comment-${comment.id}`;
    const meta = document.createElement("strong");
    meta.textContent = `${comment.author} · ${new Date(comment.created_at).toLocaleString()}`;
    const body = document.createElement("p");
    body.textContent = comment.body;
    li.append(meta, body);
    if (comment.author_id === userId) {
      const remove = document.createElement("button");
      remove.className = "link danger";
      remove.textContent = "Delete";
      remove.addEventListener("click", () => removeComment(comment.id));
      li.append(remove);
    }
    list.append(li);
  }

  async function load() {
    const res = await fetch(`/api/expenses/${expenseId}/comments`);
    if (!res.ok) return;
    list.replaceChildren();
    (await res.json()).forEach(render);
  }

  async function removeComment(commentId) {
    const res = await fetch(`/api/comments/${commentId}`, { method: "DELETE" });
    if (res.ok) document.getElementById(`comment-${commentId}`)?.remove();
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = form.elements.body.value.trim();
    if (!body) return;
    const res = await fetch(`/api/expenses/${expenseId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    if (res.ok) {
      render(await res.json());
      form.reset();
    }
  });

  load();
})();
