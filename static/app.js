const chat = document.getElementById("chat");
const statusBox = document.getElementById("payment-status");
function bubble(text, cls){const el=document.createElement("div");el.className=`bubble ${cls}`;el.textContent=text;chat.appendChild(el);chat.scrollTop=chat.scrollHeight;}
document.getElementById("askForm").addEventListener("submit",async e=>{
  e.preventDefault();const input=document.getElementById("question");const message=input.value.trim();if(!message)return;
  bubble(message,"user");input.value="";
  try{const r=await fetch("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Request failed");bubble(d.answer,"bot");document.getElementById("mode").textContent=`Response mode: ${d.mode}`;}
  catch(err){bubble("Sorry, I couldn't answer just now: "+err.message,"bot");}
});
async function setupPayPal(){
  const cfg=await fetch("/api/config").then(r=>r.json());
  if(!cfg.paypal_ready){statusBox.textContent="PayPal Sandbox is not configured yet. Add your Sandbox Client ID and Secret to .env, then restart the server.";return;}
  const old=document.querySelector('script[data-dynamic-paypal]');
  if(old)old.remove();
  const script=document.createElement("script");script.dataset.dynamicPaypal="1";
  script.src=`https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(cfg.paypal_client_id)}&currency=USD&intent=capture`;
  script.onload=()=>renderButtons();script.onerror=()=>statusBox.textContent="Could not load PayPal checkout.";
  document.head.appendChild(script);
}
function renderButtons(){
  if(!window.paypal){statusBox.textContent="PayPal SDK did not load.";return;}
  paypal.Buttons({
    createOrder:async()=>{
      const amount=document.getElementById("amount").value;
      const r=await fetch("/api/paypal/create-order",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({amount,currency:"USD"})});
      const d=await r.json();if(!r.ok)throw new Error(d.detail||"Could not create order");return d.id;
    },
    onApprove:async(data)=>{
      statusBox.textContent="Confirming payment with PayPal…";
      const r=await fetch("/api/paypal/capture-order",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({order_id:data.orderID})});
      const d=await r.json();
      statusBox.textContent=r.ok&&d.status==="COMPLETED"?"Sandbox payment completed successfully. Order: "+d.id:"Payment was not confirmed. Status: "+(d.status||"unknown");
    },
    onError:err=>{statusBox.textContent="Checkout error: "+(err.message||"Please try again.");}
  }).render("#paypal-button-container");
}
setupPayPal();
