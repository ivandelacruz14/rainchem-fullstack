// DRAFT. Have this reviewed by a legal adviser before publishing, against the Data Privacy Act of 2012 (RA 10173).
export default function PrivacyPolicy() {
  return (
    <div className="container" style={{ padding: "40px 24px 60px", maxWidth: 820 }}>
      <h1>Privacy Policy</h1>
      <p className="field-hint">Draft. Last updated: [date to be added when approved].</p>

      <h2>1. Who we are</h2>
      <p>Rainchem International, Inc. operates this website and online store (RAIMOL). Contact: [company email address to be added].</p>

      <h2>2. What we collect</h2>
      <ul>
        <li>Account details: name, email address, phone number, and password (stored only as a secure hash).</li>
        <li>Delivery details: address, for orders and service requests.</li>
        <li>Business details, if you choose a business account: business name and an optional TIN.</li>
        <li>Orders, payments (reference numbers), reviews, and chat messages, including images you send.</li>
        <li>Technical information needed to keep the site secure, such as a login session and a check that a person is not a bot.</li>
      </ul>

      <h2>3. Why we use it</h2>
      <ul>
        <li>To create and protect your account, and to sign you in.</li>
        <li>To process, deliver, and support your orders and service requests.</li>
        <li>To send order, booking, and security emails, such as verification and password codes.</li>
        <li>To answer your questions through the assistant and live chat.</li>
        <li>To meet our accounting and legal record-keeping duties.</li>
      </ul>

      <h2>4. Who we share it with</h2>
      <p>Only with the service providers needed to run the site: PayMongo (card payments), Mailjet and Resend (email), Google (if you sign in with Google), and our hosting providers (Vercel, Render, and Aiven). We do not sell your data.</p>

      <h2>5. How long we keep it</h2>
      <p>Your account stays until you delete it. Order and receipt records are kept for accounting purposes. When you delete your account, your personal details are erased, and the order records no longer link to a living account.</p>

      <h2>6. Your rights</h2>
      <p>You can view and correct your details in My Account, and you can delete your account in Settings &amp; Privacy. You may also ask us, in writing, for access to or a copy of your data, or to object to processing.</p>

      <h2>7. Security</h2>
      <p>Passwords are stored as hashes. Access to admin functions requires a password and an emailed code. Connections use HTTPS.</p>

      <h2>8. Changes</h2>
      <p>We will post any change to this policy on this page.</p>
    </div>
  );
}
