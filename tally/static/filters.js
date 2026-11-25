(function () {
  var list = document.getElementById("filter-list");
  var form = document.getElementById("new-filter");
  var range = document.createRange();

  function heading(item) {
    var owner = item.mine ? "" : ["<em> by ", item.owner, "</em>"].join("");
    return ["<strong>", item.name, "</strong>", owner].join("");
  }

  function card(item) {
    var node = document.getElementById("filter-card").content.cloneNode(true);
    var li = node.querySelector("li");
    li.prepend(range.createContextualFragment(heading(item)));
    var parts = Object.keys(item.criteria).map(function (k) { return k + ": " + item.criteria[k]; });
    li.querySelector(".pill").textContent = parts.join(", ") || "everything";
    li.querySelector("small").textContent = item.matches + " matching";
    if (item.mine) {
      var remove = document.createElement("button");
      remove.textContent = "Remove";
      remove.className = "danger";
      remove.addEventListener("click", function () {
        fetch("/filters/remove", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filter: item.key }),
        }).then(load);
      });
      li.appendChild(remove);
    }
    return node;
  }

  function load() {
    fetch("/filters/data")
      .then(function (r) { return r.json(); })
      .then(function (items) {
        list.replaceChildren();
        items.forEach(function (item) { list.appendChild(card(item)); });
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var data = new FormData(form);
    fetch("/filters/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: data.get("name"),
        shared: data.get("shared") === "on",
        criteria: { category: data.get("category"), status: data.get("status"), currency: data.get("currency") },
      }),
    }).then(function () { form.reset(); load(); });
  });

  load();
})();
