import "../styles/invoice.css";
import { peso, formatDate } from "../utils/format";
import Brand from "./Brand";

// Details printed on the company's own Sales Invoice.
const COMPANY = {
  name: "RAINCHEM INTERNATIONAL, INC.",
  address: ["4015 Le Cul De Sac Street,", "Brgy. Sun Valley,", "Parañaque City MNLA 1700 PH"],
  tel: "(Tel. No.) 823-4227 / 403-8297",
  tin: "VAT Reg. TIN 243-097-628-000",
};

function shortDate(value) {
  return value ? formatDate(value).split(",")[0] : "";
}

function termsOf(order) {
  if (order.paymentMethod === "Cash on Delivery") return "Cash on Delivery";
  return `${order.paymentMethod} (${order.paymentStatusLabel})`;
}

/** The printable receipt, laid out like the company's Sales Invoice. Used on the
 *  customer's receipt page and in the admin "Print receipt" window, so both
 *  always look the same. */
export default function ReceiptView({ order, receipt }) {
  const addr = order.address;
  const addressLines = [addr.line1, `${addr.city}, ${addr.province}`, `${addr.region} ${addr.zip}`];
  const shipped = (order.history || []).find((h) => h.status === "shipped");

  const rows = receipt.items.map((item) => ({
    qty: item.quantity,
    uom: "pc",
    description: item.discountRate > 0 ? `${item.name} (${Math.round(item.discountRate * 100)}% bulk discount)` : item.name,
    unitPrice: item.unitPrice,
    amount: item.lineTotal,
  }));
  if (receipt.shippingFee > 0) {
    rows.push({ qty: 1, uom: "svc", description: "Shipping fee", unitPrice: receipt.shippingFee, amount: receipt.shippingFee });
  }

  return (
    <div className="receipt-page invoice">
      <div className="invoice-top">
        <div className="invoice-company">
          <h2>{COMPANY.name}</h2>
          <div className="invoice-tagline"><Brand variant="wordmark" height={22} /> ENERGIZED LUBRICANTS</div>
          {COMPANY.address.map((line) => <p key={line}>{line}</p>)}
          <p>{COMPANY.tel}</p>
          <p>{COMPANY.tin}</p>
        </div>
        <div className="invoice-title">
          <div><span className="heading">Sales Invoice</span> &nbsp; <span className="number">No. {receipt.receiptNumber}</span></div>
          <p>Date: <strong>{formatDate(receipt.issuedAt)}</strong></p>
          <p>Document No.: <strong>{order.orderNumber}</strong></p>
        </div>
      </div>

      <div className="invoice-parties">
        <div>
          <span className="invoice-label">Sold To:</span>
          <p><strong>{order.customer.name}</strong></p>
          <p>{order.customer.phone} &middot; {order.customer.email}</p>
        </div>
        <div>
          <span className="invoice-label">Ship To:</span>
          <p><strong>{order.customer.name}</strong></p>
          {addressLines.map((line) => <p key={line}>{line}</p>)}
        </div>
      </div>

      <p className="invoice-style"><span className="invoice-label">Business Style:</span></p>
      <table className="invoice-grid info">
        <colgroup>
          <col style={{ width: "11%" }} /><col style={{ width: "13%" }} /><col style={{ width: "17%" }} /><col style={{ width: "12%" }} /><col style={{ width: "20%" }} /><col style={{ width: "12%" }} /><col style={{ width: "15%" }} />
        </colgroup>
        <thead>
          <tr><th>P.O. No.</th><th>Date Shipped</th><th>Terms</th><th>Due Date</th><th>D.R. No.</th><th>Cust. TIN</th><th>Sales Rep.</th></tr>
        </thead>
        <tbody>
          <tr>
            <td></td>
            <td>{shortDate(shipped?.changedAt)}</td>
            <td>{termsOf(order)}</td>
            <td></td>
            <td className="mono tracking">{order.trackingNumber}</td>
            <td></td>
            <td>Online order</td>
          </tr>
        </tbody>
      </table>

      <table className="invoice-grid items">
        <colgroup>
          <col style={{ width: "7%" }} /><col style={{ width: "8%" }} /><col /><col style={{ width: "13%" }} /><col style={{ width: "15%" }} /><col style={{ width: "16%" }} />
        </colgroup>
        <thead>
          <tr><th>Qty</th><th>UOM</th><th>Description</th><th>PBT Ref. No.</th><th>Unit Price</th><th>Amount</th></tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td className="center">{row.qty}</td>
              <td className="center">{row.uom}</td>
              <td>{row.description}</td>
              <td></td>
              <td className="num">{peso(row.unitPrice)}</td>
              <td className="num">{peso(row.amount)}</td>
            </tr>
          ))}
          <tr className="filler"><td></td><td></td><td></td><td></td><td></td><td></td></tr>
        </tbody>
      </table>

      <div className="invoice-bottom">
        <div className="invoice-note">
          Payment: {order.paymentMethod} ({order.paymentStatusLabel})
          {order.paymentReference && <><br />Reference no.: {order.paymentReference}</>}
          <br />Tracking no.: <span className="mono">{order.trackingNumber}</span>
        </div>
        <table className="invoice-totals">
          <tbody>
            <tr><td>Vatable Sales</td><td>{peso(receipt.vatableSales)}</td></tr>
            <tr><td>VAT Exempt Sales</td><td>{receipt.vatExemptSales > 0 ? peso(receipt.vatExemptSales) : ""}</td></tr>
            <tr><td>Zero Rated Sales</td><td>{receipt.zeroRatedSales > 0 ? peso(receipt.zeroRatedSales) : ""}</td></tr>
            <tr><td>VAT Amount ({receipt.vatRate}%)</td><td>{peso(receipt.vatAmount)}</td></tr>
            <tr className="due"><td>Total Amount Due</td><td>{peso(receipt.total)}</td></tr>
          </tbody>
        </table>
      </div>

      <div className="invoice-sign">
        <div>
          <div className="field"><span className="invoice-label">Prepared by:</span><div className="line" /></div>
          <div className="field"><span className="invoice-label">Checked by:</span><div className="line" /></div>
        </div>
        <div>
          <div className="field"><span className="invoice-label">Approved by:</span><div className="line" /></div>
          <div className="field"><span className="invoice-label">Noted by:</span><div className="line" /></div>
        </div>
        <div>
          <p className="invoice-terms">
            I hereby agree &amp; understand that if I do not report any complaints within 3 working days after receipt,
            the goods are deemed received in good order &amp; condition.
          </p>
          <div className="field"><span className="invoice-label">Received by:</span><div className="line" /><div className="small">(sig. over printed name)</div></div>
          <div className="field"><span className="invoice-label">Date / Time:</span><div className="line" /></div>
        </div>
      </div>

      <div className="invoice-foot">
        System-generated Sales Invoice from the Raimol online store. Prices include 12% VAT.
      </div>
    </div>
  );
}
