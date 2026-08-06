const $ = (id) => document.getElementById(id);

async function loadDefaults() {
  const stored = await chrome.storage.sync.get(['apiBase', 'accessToken']);
  $('api').value = stored.apiBase || 'http://localhost:8000/api/v1';
  $('token').value = stored.accessToken || '';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  $('url').value = tab?.url || '';
  $('title').value = tab?.title || '';

  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        title:
          document.querySelector('h1')?.innerText ||
          document.querySelector('[data-testid="job-title"]')?.innerText ||
          document.title,
        company:
          document.querySelector('[data-company]')?.innerText ||
          document.querySelector('.company')?.innerText ||
          '',
      }),
    });
    if (result?.title) $('title').value = result.title.trim();
    if (result?.company) $('company').value = result.company.trim();
  } catch {
    /* ignore content script failures on restricted pages */
  }
}

$('send').addEventListener('click', async () => {
  const apiBase = $('api').value.replace(/\/$/, '');
  const token = $('token').value.trim();
  const payload = {
    title: $('title').value.trim(),
    company: $('company').value.trim() || 'Unknown',
    apply_url: $('url').value.trim(),
    portal: 'extension',
    description: `Shared from browser: ${$('url').value.trim()}`,
  };
  await chrome.storage.sync.set({ apiBase, accessToken: token });
  $('msg').textContent = 'Sending…';
  try {
    const res = await fetch(`${apiBase}/jobs/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    $('msg').textContent = 'Sent to JobPilot ✓';
  } catch (err) {
    $('msg').textContent = `Failed: ${err.message || err}`;
  }
});

loadDefaults();
