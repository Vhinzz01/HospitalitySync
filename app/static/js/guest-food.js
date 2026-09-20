document.querySelector("#food-order-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const items = [...form.querySelectorAll("[data-menu-item]")].map((input) => ({ menu_item_id: Number(input.dataset.menuItem), quantity: Number(input.value) })).filter((item) => item.quantity > 0);
    const errorBox = document.querySelector("#order-error"); errorBox.hidden = true;
    const response = await fetch("/guest/orders", { method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({items,notes:new FormData(form).get("notes")||null}) });
    if(response.ok){window.location.reload();return} const payload=await response.json(); errorBox.textContent=typeof payload.detail==="string"?payload.detail:"Não foi possível enviar o pedido.";errorBox.hidden=false;
});
const guestFoodSocket=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/guest/ws`);guestFoodSocket.addEventListener("message",(event)=>{const payload=JSON.parse(event.data);if(payload.type==="food_order.updated")window.location.reload()});
