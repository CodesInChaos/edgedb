const MAGIC_LINK_SEND_URL = new URL(
  "../send-magic-link",
  window.location
);
const MAGIC_LINK_SENT_URL = new URL(
  "./magic-link-sent",
  window.location
);
document.addEventListener("DOMContentLoaded", function () {
  const registerForm = document.getElementById("email-factor");

  if (registerForm === null) {
    return;
  }

  registerForm.addEventListener("submit", async (event) => {
    if (event.submitter?.id !== "magic-link-signup") {
      return;
    }
    event.preventDefault();

    const formData = new FormData(/** @type {HTMLFormElement} */ registerForm);
    const email = formData.get("email");
    const provider = "builtin::local_magic_link";
    const callbackUrl = formData.get("redirect_to");
    const challenge = formData.get("challenge");

    const missingFields = [email, provider, callbackUrl, challenge].filter(
      Boolean
    );
    if (missingFields.length > 0) {
      throw new Error(
        "Missing required parameters: " + missingFields.join(", ")
      );
    }

    try {
      await register({
        email,
        provider,
        callbackUrl,
        challenge,
      });
      window.location = MAGIC_LINK_SENT_URL.href;
    } catch (err) {
      console.error("Failed to register magic link:", err);
      const url = new URL(window.location.href);
      url.searchParams.append("error", err.message);
      window.location = url.href;
    }
  });
});

async function register({ email, provider, callbackUrl, challenge }) {
  const response = await fetch(MAGIC_LINK_SEND_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      provider,
      callbackUrl,
      challenge,
    }),
  });

  if (!response.ok) {
    console.error(
      "Failed to register magic link: ",
      response.statusText
    );
    console.error(await response.text());
    throw new Error("Failed to register magic link");
  }

  try {
    return await response.json();
  } catch (e) {
    console.error("Failed to parse magic link response: ", e);
    throw new Error("Failed to parse magic link response");
  }
}
