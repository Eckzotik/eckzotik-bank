let currentProfile = null;
let selectedTheme = "blue";
let selectedAvatarMode = "preset";
let selectedAvatarValue = "😎";

function $(id){
  return document.getElementById(id);
}

function toast(msg){
  alert(msg);
}

function switchAuthTab(tab){
  $("loginTabBtn").classList.toggle("active", tab === "login");
  $("registerTabBtn").classList.toggle("active", tab === "register");
  $("loginTab").classList.toggle("active", tab === "login");
  $("registerTab").classList.toggle("active", tab === "register");
}

function setTheme(theme){
  selectedTheme = theme;
  document.body.classList.remove("theme-blue","theme-purple","theme-green","theme-gold");
  document.body.classList.add("theme-" + theme);
}

function renderAvatar(container, user){
  if(!container || !user) return;

  container.innerHTML = "";
  container.style.background = user.avatar_color || "#4f46e5";

  if(user.avatar_mode === "upload" && user.avatar_value && user.avatar_value.startsWith("data:image")){
    const img = document.createElement("img");
    img.src = user.avatar_value;
    container.appendChild(img);
  } else {
    container.textContent = user.avatar_value || user.display_name.charAt(0).toUpperCase();
  }
}

function renderPresetAvatars(presets, currentValue){
  const wrap = $("presetAvatarList");
  wrap.innerHTML = "";

  presets.forEach(av => {
    const btn = document.createElement("button");
    btn.className = "preset-avatar-btn" + (av === currentValue ? " active" : "");
    btn.textContent = av;
    btn.onclick = () => {
      selectedAvatarMode = "preset";
      selectedAvatarValue = av;
      document.querySelectorAll(".preset-avatar-btn").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");
    };
    wrap.appendChild(btn);
  });
}

function renderProfile(){
  if(!currentProfile) return;

  const user = currentProfile.user;
  const cards = currentProfile.cards;
  const contacts = currentProfile.contacts;
  const history = currentProfile.history;

  $("topDisplayName").innerText = user.display_name;
  renderAvatar($("avatarMini"), user);

  $("profileDisplayName").value = user.display_name;
  $("profileAvatarColor").value = user.avatar_color || "#4f46e5";
  $("profileUsername").innerText = user.username;
  $("profilePhone").innerText = user.phone || "-";
  $("profileReferral").innerText = user.referral_code;
  $("languageSelect").value = user.language || "ru";
  $("maxCardsInfo").innerText = currentProfile.max_cards || 5;

  selectedAvatarMode = user.avatar_mode || "preset";
  selectedAvatarValue = user.avatar_value || "😎";
  renderPresetAvatars(currentProfile.preset_avatars || [], selectedAvatarValue);

  setTheme(user.theme || "blue");

  const mainCard = cards.find(c => c.is_main === 1) || cards[0];
  if(mainCard){
    $("mainBalance").innerText = `${Number(mainCard.balance).toFixed(2)} ${mainCard.currency}`;
  }

  renderCards(cards);
  renderContacts(contacts);
  renderHistory(history);
  fillCardSelectors(cards);
}

function renderCards(cards){
  const wrap = $("cardsList");
  wrap.innerHTML = "";

  cards.forEach(card => {
    const blockedText = card.is_blocked ? "ЗАБЛОКИРОВАНА" : "АКТИВНА";

    const div = document.createElement("div");
    div.className = `bank-card ${card.skin || "ocean"}`;

    div.innerHTML = `
      <div class="card-top">
        <div class="card-title">${card.card_name}${card.is_main ? " · MAIN" : ""}</div>
        <div class="card-badge">${card.card_type === "child" ? "CHILD" : "ADULT"}</div>
      </div>

      <div class="card-number">${card.card_number}</div>

      <div class="card-meta">
        <span>${card.currency}</span>
        <span>${card.expiry}</span>
        <span>CVV ${card.cvv}</span>
      </div>

      <div class="card-balance">${Number(card.balance).toFixed(2)} ${card.currency}</div>

      <div class="card-limits">
        Лимит/перевод: ${Number(card.per_transfer_limit).toFixed(2)} ${card.currency}<br>
        Дневной лимит: ${Number(card.daily_limit).toFixed(2)} ${card.currency}
      </div>

      <div class="card-status">${blockedText}</div>

      <div class="card-actions">
        <button class="mini-btn" onclick="setMainCard(${card.id})">Сделать главной</button>
        <button class="mini-btn" onclick="convertCardPrompt(${card.id}, '${card.currency}')">Конвертация</button>
        <button class="mini-btn" onclick="toggleCardBlock(${card.id})">${card.is_blocked ? "Разблокировать" : "Заблокировать"}</button>
      </div>
    `;
    wrap.appendChild(div);
  });
}

function renderContacts(contacts){
  const wrap = $("contactsList");
  wrap.innerHTML = "";

  if(!contacts.length){
    wrap.innerHTML = `<div class="muted">Контактов пока нет</div>`;
    return;
  }

  contacts.forEach(contact => {
    const div = document.createElement("div");
    div.className = "contact-card";

    div.innerHTML = `
      <div class="contact-top">
        <div>
          <div class="contact-name">${contact.contact_name}</div>
          <div class="contact-sub">username: ${contact.contact_username || "-"}</div>
          <div class="contact-sub">card: ${contact.contact_card || "-"}</div>
        </div>
        <button class="mini-btn" onclick="deleteContact(${contact.id})">Удалить</button>
      </div>
      <div class="contact-actions">
        ${contact.contact_card ? `<button class="mini-btn" onclick="quickTransferToContact('${contact.contact_card}')">Быстрый перевод</button>` : ""}
      </div>
    `;
    wrap.appendChild(div);
  });
}

function renderHistory(items){
  const wrap = $("historyList");
  wrap.innerHTML = "";

  if(!items.length){
    wrap.innerHTML = `<div class="muted">История пуста</div>`;
    return;
  }

  items.forEach(item => {
    const row = document.createElement("div");
    const cls = item.amount >= 0 ? "amount-pos" : "amount-neg";
    const sign = item.amount >= 0 ? "+" : "";

    row.className = "history-row";
    row.innerHTML = `
      <div>
        <div class="history-title">${item.title}</div>
        <div class="history-sub">${item.subtitle} · ${item.created_at}</div>
      </div>
      <div class="${cls}">${sign}${Number(item.amount).toFixed(2)}</div>
    `;
    wrap.appendChild(row);
  });
}

function fillCardSelectors(cards){
  const fromSelect = $("fromCardSelect");
  const fineSelect = $("fineCardSelect");
  fromSelect.innerHTML = "";
  fineSelect.innerHTML = "";

  cards.forEach(card => {
    const label = `${card.card_name} · ${card.card_number} · ${Number(card.balance).toFixed(2)} ${card.currency}`;

    const opt1 = document.createElement("option");
    opt1.value = card.id;
    opt1.innerText = label;
    fromSelect.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = card.id;
    opt2.innerText = label;
    fineSelect.appendChild(opt2);
    fromSelect.appendChild(opt1);
  });
}

function openSection(id){
  document.querySelectorAll(".panel").forEach(el => el.classList.add("hidden"));
  if(id){
    $(id).classList.remove("hidden");
  }
}

async function refreshProfile(){
  if(!currentProfile) return;

  const username = currentProfile.user.username;
  const res = await fetch(`/api/profile/${username}`);
  const data = await res.json();

  if(!data.ok){
    toast(data.error || "Ошибка обновления");
    return;
  }

  currentProfile = data.profile;
  renderProfile();
}

function refreshAll(){
  refreshProfile();
}

async function registerUser(){
  const payload = {
    display_name: $("registerDisplayName").value.trim(),
    username: $("registerUsername").value.trim(),
    phone: $("registerPhone").value.trim(),
    password: $("registerPassword").value.trim(),
    referral_code: $("registerReferral").value.trim()
  };

  const res = await fetch("/api/register", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if(!data.ok){
    toast(data.error || "Ошибка регистрации");
    return;
  }

  currentProfile = data.profile;
  $("authScreen").classList.add("hidden");
  $("appScreen").classList.remove("hidden");
  renderProfile();
}

async function login(){
  const payload = {
    username: $("loginUsername").value.trim(),
    password: $("loginPassword").value.trim()
  };

  const res = await fetch("/api/login", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if(!data.ok){
    toast(data.error || "Ошибка входа");
    return;
  }

  currentProfile = data.profile;
  $("authScreen").classList.add("hidden");
  $("appScreen").classList.remove("hidden");
  renderProfile();
}

async function saveProfile(){
  if(!currentProfile) return;

  const fileInput = $("avatarUpload");
  let avatarMode = selectedAvatarMode;
  let avatarValue = selectedAvatarValue;

  if(fileInput.files && fileInput.files[0]){
    avatarMode = "upload";
    avatarValue = await fileToBase64(fileInput.files[0]);
  }

  const payload = {
    username: currentProfile.user.username,
    display_name: $("profileDisplayName").value.trim(),
    avatar_color: $("profileAvatarColor").value.trim(),
    avatar_mode: avatarMode,
    avatar_value: avatarValue
  };

  const res = await fetch("/api/profile/update", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if(!data.ok){
    toast(data.error || "Ошибка профиля");
    return;
  }

  toast("Профиль сохранён");
  fileInput.value = "";
  await refreshProfile();
}

function fileToBase64(file){
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function pickTheme(theme){
  setTheme(theme);
}

async function saveSettings(){
  if(!currentProfile) return;

  const payload = {
    username: currentProfile.user.username,
    theme: selectedTheme,
    language: $("languageSelect").value
  };

  const res = await fetch("/api/settings/update", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if(!data.ok){
    toast("Ошибка настроек");
    return;
  }

  toast("Настройки сохранены");
  await refreshProfile();
}

async function createCard(){
  if(!currentProfile) return;

  const payload = {
    username: currentProfile.user.username,
    card_name: $("newCardName").value.trim(),
    currency: $("newCardCurrency").value,
    skin: $("newCardSkin").value,
    card_type: $("newCardType").value
  };

  const res = await fetch("/api/cards/create", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if(!data.ok){
    toast(data.error || "Ошибка создания карты");
    return;
  }

  toast("Карта создана");
  $("newCardName").value = "";
  await refreshProfile();
}

async function setMainCard(cardId){
  if(!currentProfile) return;

  const res = await fetch("/api/cards/set_main", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      username: currentProfile.user.username,
      card_id: cardId
    })
  });

  const data = await res.json();
  if(!data.ok){
    toast("Ошибка выбора карты");
    return;
  }

  await refreshProfile();
}

async function toggleCardBlock(cardId){
  if(!currentProfile) return;

  const res = await fetch("/api/cards/toggle_block", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      username: currentProfile.user.username,
      card_id: cardId
    })
  });

  const data = await res.json();
  if(!data.ok){
    toast(data.error || "Ошибка блокировки");
    return;
  }

  await refreshProfile();
}

async function addContact(){
  if(!currentProfile) return;

  const payload = {
    username: currentProfile.user.username,
    contact_name: $("contactName").value.trim(),
    contact_username: $("contactUsername").value.trim(),
    contact_card: $("contactCard").value.trim()
  };

  const res = await fetch("/api/contacts/add", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if(!data.ok){
    toast(data.error || "Ошибка контакта");
    return;
  }

  $("contactName").value = "";
  $("contactUsername").value = "";
  $("contactCard").value = "";
  await refreshProfile();
}

async function deleteContact(contactId){
  if(!currentProfile) return;

  const res = await fetch("/api/contacts/delete", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      username: currentProfile.user.username,
      contact_id: contactId
    })
  });

  const data = await res.json();
  if(!data.ok){
    toast("Ошибка удаления");
    return;
  }

  await refreshProfile();
}

function quickTransferToContact(cardNumber){
  openSection("transferSection");
  $("targetCardNumber").value = cardNumber;
}

async function sendCardTransfer(){
  if(!currentProfile) return;

  const payload = {
    username: currentProfile.user.username,
    from_card_id: $("fromCardSelect").value,
    target_card_number: $("targetCardNumber").value.trim(),
    amount: $("transferAmount").value.trim()
  };

  const res = await fetch("/api/transfer/card_to_card", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if(!data.ok){
    toast(data.error || "Ошибка перевода");
    return;
  }

  $("targetCardNumber").value = "";
  $("transferAmount").value = "";
  toast("Перевод отправлен");
  await refreshProfile();
}

async function payFine(){
  if(!currentProfile) return;

  const payload = {
    username: currentProfile.user.username,
    card_id: $("fineCardSelect").value,
    reason: $("fineReason").value.trim(),
    amount: $("fineAmount").value.trim()
  };

  const res = await fetch("/api/pay/fine", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if(!data.ok){
    toast(data.error || "Ошибка оплаты штрафа");
    return;
  }

  $("fineReason").value = "";
  $("fineAmount").value = "";
  toast("Штраф оплачен");
  await refreshProfile();
}

async function convertCardPrompt(cardId, fromCurrency){
  const toCurrency = prompt(`Конвертировать ${fromCurrency} в какую валюту? UAH/USD/EUR/PLN`, "USD");
  if(!toCurrency) return;

  const res = await fetch("/api/cards/convert", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      username: currentProfile.user.username,
      card_id: cardId,
      to_currency: toCurrency.toUpperCase()
    })
  });

  const data = await res.json();
  if(!data.ok){
    toast(data.error || "Ошибка конвертации");
    return;
  }

  toast("Валюта карты изменена");
  await refreshProfile();
}

function logout(){
  currentProfile = null;
  $("appScreen").classList.add("hidden");
  $("authScreen").classList.remove("hidden");
  switchAuthTab("login");
}

window.addEventListener("load", () => {
  switchAuthTab("login");
  setTheme("blue");
});