document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      links.classList.toggle("nav-open", !expanded);
    });
  }

  const accountTrigger = document.querySelector("#account-trigger");
  const accountMenu = document.querySelector("#account-menu");
  if (accountTrigger && accountMenu) {
    const closeAccountMenu = () => {
      accountMenu.hidden = true;
      accountTrigger.setAttribute("aria-expanded", "false");
    };

    accountTrigger.addEventListener("click", () => {
      const isOpen = accountTrigger.getAttribute("aria-expanded") === "true";
      accountMenu.hidden = isOpen;
      accountTrigger.setAttribute("aria-expanded", String(!isOpen));
    });

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".nav-account")) closeAccountMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeAccountMenu();
        accountTrigger.focus();
      }
    });
  }

  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-google-signin]").forEach((button) => {
    button.addEventListener("click", () => {
      const note = button.parentElement.querySelector("[data-google-note]");
      if (note) note.hidden = false;
    });
  });

  const volumeSlider = document.querySelector("#id_notification_volume");
  const volumeValue = document.querySelector("#volume-value");
  if (volumeSlider && volumeValue) {
    volumeSlider.addEventListener("input", () => {
      volumeValue.value = volumeSlider.value;
      volumeValue.textContent = volumeSlider.value;
    });
  }

  let audioContext;
  const prepareAudio = () => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    audioContext ||= new AudioContextClass();
    if (audioContext.state === "suspended") audioContext.resume();
  };
  document.addEventListener("pointerdown", prepareAudio, { once: true });
  document.addEventListener("keydown", prepareAudio, { once: true });

  const playNotificationSound = (volume) => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass || volume <= 0) return;
    audioContext ||= new AudioContextClass();
    if (audioContext.state === "suspended") audioContext.resume();
    const startAt = audioContext.currentTime;
    const gain = audioContext.createGain();
    gain.gain.setValueAtTime((volume / 100) * 0.22, startAt);
    gain.gain.exponentialRampToValueAtTime(0.001, startAt + 0.36);
    gain.connect(audioContext.destination);
    [660, 880].forEach((frequency, index) => {
      const oscillator = audioContext.createOscillator();
      const noteStart = startAt + index * 0.13;
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, noteStart);
      oscillator.connect(gain);
      oscillator.start(noteStart);
      oscillator.stop(noteStart + 0.2);
    });
  };

  document.querySelector("[data-test-notification-sound]")?.addEventListener("click", () => {
    prepareAudio();
    playNotificationSound(Number(volumeSlider?.value ?? body.dataset.notificationVolume ?? 45));
  });

  const statusUrl = body.dataset.notificationStatusUrl;
  if (statusUrl) {
    let latestId = Number(body.dataset.latestNotificationId || 0);
    const checkForNotifications = async () => {
      if (document.hidden) return;
      const response = await fetch(statusUrl, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) return;
      const status = await response.json();
      const newNotification = status.latest_id > latestId;
      if (!status.enabled || !newNotification) {
        latestId = status.latest_id;
        return;
      }
      latestId = status.latest_id;
      playNotificationSound(status.volume);
    };
    window.setInterval(() => {
      checkForNotifications();
    }, 20000);
  }

  document.querySelectorAll(".message-close").forEach((button) => {
    button.addEventListener("click", () => button.closest(".message")?.remove());
  });
});
