async function onSessionReady() {
  if (!session) {
    showAuth();
    return;
  }

  // Avoid processing the same access token twice
  if (session.access_token === lastProcessedAccessToken) return;
  lastProcessedAccessToken = session.access_token;

  el('user-email').textContent = session.user.email || 'Investigator';

  if (!env.requireMfa) {
    await completeSignIn();
    return;
  }

  const aal = decodeAal(session.access_token);
  if (aal === 'aal2') {
    await completeSignIn();
    return;
  }

  try {
    const prepared = await prepareMfaStep();
    if (prepared.type === 'challenge') {
      await challengeMfa(prepared.factorId);
    } else {
      await enrollMfa();
    }
  } catch (err) {
    console.error('MFA flow failed:', err);
    showToast(err.message || 'MFA setup failed. Please sign in again.', 'error');
    await supabase.auth.signOut();
    session = null;
    showAuth();
  }
}

async function cleanupStaleMfaFactors() {
  const { data, error } = await supabase.auth.mfa.listFactors();
  if (error) throw error;

  const unverified = (data?.totp || []).filter((f) => f.status === 'unverified');

  for (const factor of unverified) {
    try {
      await supabase.auth.mfa.unenroll({ factorId: factor.id });
      console.info('Removed stale unverified MFA factor:', factor.id);
    } catch (err) {
      console.warn('Could not remove stale MFA factor:', factor.id, err);
      // Keep going; we will fail later if the stale factor cannot be removed.
    }
  }
}

async function prepareMfaStep() {
  const { data: factorsData, error } = await supabase.auth.mfa.listFactors();
  if (error) throw error;

  const allTotp = factorsData.totp || [];
  const verified = allTotp.filter((f) => f.status === 'verified');

  if (verified.length > 0) {
    return { type: 'challenge', factorId: verified[0].id };
  }

  // Always remove stale unverified factors before enrolling a new one.
  await cleanupStaleMfaFactors();

  const { data: refreshedFactors, error: refreshedError } = await supabase.auth.mfa.listFactors();
  if (refreshedError) throw refreshedError;

  const remainingVerified = (refreshedFactors?.totp || []).filter((f) => f.status === 'verified');
  if (remainingVerified.length > 0) {
    return { type: 'challenge', factorId: remainingVerified[0].id };
  }

  return { type: 'enroll' };
}

async function enrollMfa() {
  try {
    const { data, error } = await supabase.auth.mfa.enroll({ factorType: 'totp' });
    if (error) {
      const msg = (error.message || '').toLowerCase();

      // Handle stale factors robustly
      if (msg.includes('already exists') || msg.includes('unverified') || msg.includes('factor')) {
        await cleanupStaleMfaFactors();

        const prepared = await prepareMfaStep();
        if (prepared.type === 'challenge') {
          await challengeMfa(prepared.factorId);
          return;
        }

        const retry = await supabase.auth.mfa.enroll({ factorType: 'totp' });
        if (retry.error) throw retry.error;

        const factor = retry.data;
        el('mfa-factor-id').value = factor.id;
        const qrContainer = el('mfa-qr');
        if (qrContainer) {
          qrContainer.innerHTML = `<div class="qr-wrap">${factor.totp.qr_code}</div>`;
        }
        showView('mfa');
        return;
      }

      throw error;
    }

    el('mfa-factor-id').value = data.id;
    const qrContainer = el('mfa-qr');
    if (qrContainer) {
      qrContainer.innerHTML = `<div class="qr-wrap">${data.totp.qr_code}</div>`;
    }
    showView('mfa');
  } catch (err) {
    const msg = err?.message || 'Failed to set up MFA.';
    console.error('MFA enroll failed:', err);

    if (msg.toLowerCase().includes('already exists') || msg.toLowerCase().includes('unverified')) {
      throw new Error(
        'Your MFA setup is stale. Please sign out, sign back in, and try again. If it still fails, contact an administrator.'
      );
    }

    throw err;
  }
}
