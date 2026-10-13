"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, type CanonicalValueRevision, type CountryOption, type DynamicCaseStatus, type Person } from "@/lib/api";

const actor = process.env.NEXT_PUBLIC_WORKFLOW_ACTOR ?? "manual-ui";

function textValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function triState(value: FormDataEntryValue | null): boolean | null {
  if (value === "yes") return true;
  if (value === "no") return false;
  return null;
}

function triDefault(value: unknown) {
  return value === true ? "yes" : value === false ? "no" : "unknown";
}

function sameValue(left: unknown, right: unknown) {
  return (left ?? null) === (right ?? null);
}

export function canonicalFieldId(path: string) {
  return `canonical-${path.replaceAll(".", "-")}`;
}

export function CanonicalIntakeSection({ caseId, status, revisions, people, onChanged }: {
  caseId: string;
  status: DynamicCaseStatus;
  revisions: CanonicalValueRevision[];
  people: Person[];
  onChanged: () => Promise<void>;
}) {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const values = status.canonical_values;
  useEffect(() => { api.listCountryOptions().then(setCountries).catch(() => setCountries([])); }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    const data = new FormData(event.currentTarget);
    const optional = (name: string) => String(data.get(name) ?? "").trim() || null;
    const expectedRevision = (fieldPath: string) => Math.max(0, ...revisions.filter(item => item.field_path === fieldPath).map(item => item.revision));
    const decision = (field_path: string, value_json: unknown) => ({ field_path, value_json, expected_revision: expectedRevision(field_path) });
    const sponsorExists = triState(data.get("sponsor_exists"));
    const hostExists = triState(data.get("host_exists"));
    const mailingSame = triState(data.get("mailing_same_as_residential"));
    const fundsText = String(data.get("available_funds_amount") ?? "").trim();
    const proposed = [
      decision("case.visa_type", String(data.get("visa_type") ?? "").trim()),
      decision("applicant.given_names", String(data.get("given_names") ?? "").trim()),
      decision("applicant.family_name", String(data.get("family_name") ?? "").trim()),
      decision("applicant.biography.date_of_birth", optional("date_of_birth")),
      decision("applicant.biography.other_names", optional("other_names")),
      decision("applicant.biography.sex", optional("sex")),
      decision("applicant.biography.birth_city", optional("birth_city")),
      decision("applicant.biography.birth_state_province", optional("birth_state_province")),
      decision("applicant.biography.birth_country_code", optional("birth_country_code")),
      decision("applicant.biography.marital_status", optional("marital_status")),
      decision("applicant.citizenship.primary", optional("primary_citizenship")),
      decision("applicant.current_residence.country_code", optional("current_residence_country")),
      decision("applicant.passport.number", optional("passport_number")),
      decision("applicant.passport.issuing_country_code", optional("passport_issuing_country")),
      decision("applicant.passport.issue_date", optional("passport_issue_date")),
      decision("applicant.passport.expiry_date", optional("passport_expiry_date")),
      decision("applicant.residential_address.street_number", optional("address_street_number")),
      decision("applicant.residential_address.street_name", optional("address_street_name")),
      decision("applicant.residential_address.city", optional("address_city")),
      decision("applicant.residential_address.state_province", optional("address_state")),
      decision("applicant.residential_address.postal_code", optional("address_postal_code")),
      decision("applicant.residential_address.country_code", optional("address_country")),
      decision("application.mailing_same_as_residential", mailingSame),
      decision("application.official_application_date", optional("official_application_date")),
      decision("contact.email", optional("email")), decision("contact.phone", optional("phone")),
      decision("trip.purpose", optional("purpose")), decision("destination.country_code", optional("destination")),
      decision("trip.imm5257_purpose_code", optional("imm5257_purpose_code")),
      decision("trip.arrival_date", optional("arrival_date")),
      decision("trip.departure_date", optional("departure_date")),
      decision("trip.available_funds_amount", fundsText ? Number(fundsText) : null),
      decision("trip.available_funds_currency", optional("available_funds_currency")),
      decision("trip.funds_source_reference", optional("funds_source_reference")),
      decision("sponsor.exists", sponsorExists),
      decision("sponsor.person_id", sponsorExists === false ? null : optional("sponsor_person_id")),
      decision("host.exists", hostExists),
      decision("host.person_id", hostExists === false ? null : optional("host_person_id")),
      decision("trip.payer", optional("payer")), decision("commercial.instructions", optional("commercial_instructions")),
      decision("special.circumstances", optional("special_circumstances")), decision("additional.notes", optional("additional_notes")),
    ].filter(item => !sameValue(values[item.field_path], item.value_json));
    try {
      if (!proposed.length) { setMessage("No canonical information changed."); return; }
      await api.applyCanonicalDecisions(caseId, proposed, actor);
      setMessage("Canonical intake information saved and requirements recalculated.");
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Canonical information could not be saved.");
    } finally { setBusy(false); }
  }

  return <section className="section-card" id="canonical-intake">
    <div className="section-heading"><div><h2>Canonical intake information</h2><span className="muted">Verified application information collected from forms, documents, and employee review. This is the information used to prepare the official visa application. Missing or conflicting details must be resolved before finalization.</span></div></div>
    {message && <div className="success-message" role="status">{message}</div>}{error && <div className="form-error" role="alert">{error}</div>}
    <form className="form-grid" onSubmit={save} key={`${JSON.stringify(values)}:${countries.length}`}>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.given_names")}>Given names</label><input id={canonicalFieldId("applicant.given_names")} data-field-path="applicant.given_names" name="given_names" required defaultValue={textValue(values["applicant.given_names"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.family_name")}>Family name</label><input id={canonicalFieldId("applicant.family_name")} data-field-path="applicant.family_name" name="family_name" required defaultValue={textValue(values["applicant.family_name"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.biography.date_of_birth")}>Date of birth</label><input id={canonicalFieldId("applicant.biography.date_of_birth")} data-field-path="applicant.biography.date_of_birth" name="date_of_birth" type="date" defaultValue={textValue(values["applicant.biography.date_of_birth"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.biography.sex")}>Sex</label><select id={canonicalFieldId("applicant.biography.sex")} data-field-path="applicant.biography.sex" name="sex" defaultValue={textValue(values["applicant.biography.sex"])}><option value="">Unresolved</option><option value="female">Female</option><option value="male">Male</option><option value="another_gender">Another gender</option><option value="unknown">Unknown</option></select></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.biography.birth_city")}>City of birth</label><input id={canonicalFieldId("applicant.biography.birth_city")} data-field-path="applicant.biography.birth_city" name="birth_city" defaultValue={textValue(values["applicant.biography.birth_city"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.biography.birth_state_province")}>State / province of birth</label><input id={canonicalFieldId("applicant.biography.birth_state_province")} data-field-path="applicant.biography.birth_state_province" name="birth_state_province" defaultValue={textValue(values["applicant.biography.birth_state_province"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.biography.birth_country_code")}>Country of birth</label><select id={canonicalFieldId("applicant.biography.birth_country_code")} data-field-path="applicant.biography.birth_country_code" name="birth_country_code" defaultValue={textValue(values["applicant.biography.birth_country_code"])}><option value="">Unresolved</option>{countries.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}</select></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.biography.marital_status")}>Marital status</label><select id={canonicalFieldId("applicant.biography.marital_status")} data-field-path="applicant.biography.marital_status" name="marital_status" defaultValue={textValue(values["applicant.biography.marital_status"])}><option value="">Unresolved</option><option value="single">Single</option><option value="married">Married</option><option value="common_law">Common-law</option><option value="widowed">Widowed</option><option value="divorced">Divorced</option><option value="separated">Separated</option><option value="annulled_marriage">Annulled marriage</option><option value="unknown">Unknown</option></select></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.citizenship.primary")}>Primary citizenship</label><select id={canonicalFieldId("applicant.citizenship.primary")} data-field-path="applicant.citizenship.primary" name="primary_citizenship" defaultValue={textValue(values["applicant.citizenship.primary"])}><option value="">Unresolved</option>{countries.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}</select></div>
      <div className="field field-full"><label htmlFor={canonicalFieldId("applicant.biography.other_names")}>Other names</label><input id={canonicalFieldId("applicant.biography.other_names")} data-field-path="applicant.biography.other_names" name="other_names" defaultValue={textValue(values["applicant.biography.other_names"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.current_residence.country_code")}>Current country of residence</label><select id={canonicalFieldId("applicant.current_residence.country_code")} name="current_residence_country" defaultValue={textValue(values["applicant.current_residence.country_code"])}><option value="">Unresolved</option>{countries.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}</select></div>
      <h3 className="field-full">Passport</h3>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.passport.number")}>Passport number</label><input id={canonicalFieldId("applicant.passport.number")} name="passport_number" defaultValue={textValue(values["applicant.passport.number"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.passport.issuing_country_code")}>Issuing country</label><select id={canonicalFieldId("applicant.passport.issuing_country_code")} name="passport_issuing_country" defaultValue={textValue(values["applicant.passport.issuing_country_code"])}><option value="">Unresolved</option>{countries.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}</select></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.passport.issue_date")}>Passport issue date</label><input id={canonicalFieldId("applicant.passport.issue_date")} name="passport_issue_date" type="date" defaultValue={textValue(values["applicant.passport.issue_date"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.passport.expiry_date")}>Passport expiry date</label><input id={canonicalFieldId("applicant.passport.expiry_date")} name="passport_expiry_date" type="date" defaultValue={textValue(values["applicant.passport.expiry_date"])} /></div>
      <h3 className="field-full">Contact and residential address</h3>
      <div className="field"><label htmlFor={canonicalFieldId("contact.email")}>Email</label><input id={canonicalFieldId("contact.email")} name="email" type="email" defaultValue={textValue(values["contact.email"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("contact.phone")}>Phone</label><input id={canonicalFieldId("contact.phone")} name="phone" defaultValue={textValue(values["contact.phone"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.residential_address.street_number")}>Street number</label><input id={canonicalFieldId("applicant.residential_address.street_number")} name="address_street_number" defaultValue={textValue(values["applicant.residential_address.street_number"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.residential_address.street_name")}>Street name</label><input id={canonicalFieldId("applicant.residential_address.street_name")} name="address_street_name" defaultValue={textValue(values["applicant.residential_address.street_name"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.residential_address.city")}>City</label><input id={canonicalFieldId("applicant.residential_address.city")} name="address_city" defaultValue={textValue(values["applicant.residential_address.city"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.residential_address.state_province")}>State / province</label><input id={canonicalFieldId("applicant.residential_address.state_province")} name="address_state" defaultValue={textValue(values["applicant.residential_address.state_province"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.residential_address.postal_code")}>Postal code</label><input id={canonicalFieldId("applicant.residential_address.postal_code")} name="address_postal_code" defaultValue={textValue(values["applicant.residential_address.postal_code"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("applicant.residential_address.country_code")}>Address country</label><select id={canonicalFieldId("applicant.residential_address.country_code")} name="address_country" defaultValue={textValue(values["applicant.residential_address.country_code"])}><option value="">Unresolved</option>{countries.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}</select></div>
      <div className="field"><label htmlFor={canonicalFieldId("application.mailing_same_as_residential")}>Mailing address same as residential</label><select id={canonicalFieldId("application.mailing_same_as_residential")} name="mailing_same_as_residential" defaultValue={triDefault(values["application.mailing_same_as_residential"])}><option value="unknown">Unknown</option><option value="yes">Yes</option><option value="no">No</option></select></div>
      <div className="field"><label htmlFor={canonicalFieldId("application.official_application_date")}>Official application date</label><input id={canonicalFieldId("application.official_application_date")} name="official_application_date" type="date" defaultValue={textValue(values["application.official_application_date"])} /></div>
      <div className="field"><label htmlFor="canonical-visa">Visa type</label><input id="canonical-visa" name="visa_type" required defaultValue={textValue(values["case.visa_type"])} /></div>
      <div className="field"><label htmlFor="canonical-destination">Destination country</label><input id="canonical-destination" name="destination" maxLength={3} defaultValue={textValue(values["destination.country_code"])} /></div>
      <div className="field field-full"><label htmlFor={canonicalFieldId("trip.purpose")}>Travel purpose</label><input id={canonicalFieldId("trip.purpose")} name="purpose" defaultValue={textValue(values["trip.purpose"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.imm5257_purpose_code")}>Purpose of visit to Canada (IMM5257)</label><select id={canonicalFieldId("trip.imm5257_purpose_code")} name="imm5257_purpose_code" defaultValue={textValue(values["trip.imm5257_purpose_code"])}><option value="">Unresolved / not selected</option><option value="Tourism">Tourism</option><option value="Family Visit">Family Visit</option><option value="Business">Business</option></select><span className="muted">Select the purpose category used on the official Canadian visitor visa application. This is separate from your detailed travel-purpose description.</span></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.arrival_date")}>Arrival date</label><input id={canonicalFieldId("trip.arrival_date")} name="arrival_date" type="date" defaultValue={textValue(values["trip.arrival_date"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.departure_date")}>Departure date</label><input id={canonicalFieldId("trip.departure_date")} name="departure_date" type="date" defaultValue={textValue(values["trip.departure_date"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.available_funds_amount")}>Available funds</label><input id={canonicalFieldId("trip.available_funds_amount")} name="available_funds_amount" type="number" min="0" step="0.01" defaultValue={values["trip.available_funds_amount"] == null ? "" : String(values["trip.available_funds_amount"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.available_funds_currency")}>Funds currency</label><input id={canonicalFieldId("trip.available_funds_currency")} name="available_funds_currency" maxLength={3} defaultValue={textValue(values["trip.available_funds_currency"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.funds_source_reference")}>Funds source</label><input id={canonicalFieldId("trip.funds_source_reference")} name="funds_source_reference" defaultValue={textValue(values["trip.funds_source_reference"])} /></div>
      <div className="field"><label htmlFor={canonicalFieldId("sponsor.exists")}>Financial sponsor</label><select id={canonicalFieldId("sponsor.exists")} name="sponsor_exists" defaultValue={triDefault(values["sponsor.exists"])}><option value="unknown">Unknown</option><option value="yes">Yes</option><option value="no">No</option></select></div>
      <div className="field"><label htmlFor={canonicalFieldId("sponsor.person_id")}>Sponsor identity</label><select id={canonicalFieldId("sponsor.person_id")} name="sponsor_person_id" defaultValue={textValue(values["sponsor.person_id"])}><option value="">Not selected</option>{people.filter(person => !person.roles.includes("applicant")).map(person => <option key={person.id} value={person.id}>{person.first_name} {person.last_name}</option>)}</select></div>
      <div className="field"><label htmlFor={canonicalFieldId("host.exists")}>Host in Canada</label><select id={canonicalFieldId("host.exists")} name="host_exists" defaultValue={triDefault(values["host.exists"])}><option value="unknown">Unknown</option><option value="yes">Yes</option><option value="no">No</option></select></div>
      <div className="field"><label htmlFor={canonicalFieldId("host.person_id")}>Host identity</label><select id={canonicalFieldId("host.person_id")} name="host_person_id" defaultValue={textValue(values["host.person_id"])}><option value="">Not selected</option>{people.filter(person => !person.roles.includes("applicant")).map(person => <option key={person.id} value={person.id}>{person.first_name} {person.last_name}</option>)}</select></div>
      <div className="field"><label htmlFor={canonicalFieldId("trip.payer")}>Trip payer</label><select id={canonicalFieldId("trip.payer")} name="payer" defaultValue={textValue(values["trip.payer"])}><option value="">Unknown</option><option value="applicant">Applicant / self-funded</option><option value="sponsor">Sponsor</option><option value="mixed">Mixed funding</option><option value="other">Other</option></select></div>
      <div className="field field-full"><label htmlFor="canonical-instructions">Commercial instructions</label><textarea id="canonical-instructions" name="commercial_instructions" defaultValue={textValue(values["commercial.instructions"])} /></div>
      <div className="field field-full"><label htmlFor="canonical-special">Special circumstances</label><textarea id="canonical-special" name="special_circumstances" defaultValue={textValue(values["special.circumstances"])} /></div>
      <div className="field field-full"><label htmlFor="canonical-notes">Additional notes</label><textarea id="canonical-notes" name="additional_notes" defaultValue={textValue(values["additional.notes"])} /></div>
      <div className="button-row field-full"><button className="button" disabled={busy}>{busy ? "Saving…" : "Save canonical information"}</button></div>
    </form>
  </section>;
}
