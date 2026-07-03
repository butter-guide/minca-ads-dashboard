/**
 * À coller dans : ton Google Sheet → Extensions → Apps Script (remplace tout le contenu).
 * Puis : Déployer → Nouveau déploiement → Application Web
 *   - Exécuter en tant que : Moi
 *   - Qui a accès : Tout le monde
 * Copie l'URL qui finit par /exec et donne-la à Claude.
 */

const SECRET = "minca-dash-8f3k9x2q";  // doit être identique à SHEETS_SECRET dans .env

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    if (SECRET && data.secret !== SECRET) {
      return ContentService.createTextOutput("ERREUR: secret invalide");
    }
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    writeSheet(ss, "Par ad", data.par_ad, true);
    writeSheet(ss, "Résumé", data.resume, false);
    return ContentService.createTextOutput("OK");
  } catch (err) {
    return ContentService.createTextOutput("ERREUR: " + err);
  }
}

function writeSheet(ss, name, values, freezeHeader) {
  if (!values || !values.length) return;
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  sh.clearContents();
  sh.getRange(1, 1, values.length, values[0].length).setValues(values);
  sh.setFrozenRows(freezeHeader ? 1 : 0);
}
