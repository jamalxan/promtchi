"""CRM Kanban — qabul qilish mezonlariga mos testlar (12-bo'lim)."""
import asyncio


def test_honeypot_silently_ignored(client):
    r = client.post("/api/leads", json={
        "name": "Bot", "phone": "+998900000999", "message": "spam",
        "website": "http://spam.example",
    })
    assert r.status_code == 201
    assert r.json()["id"] == 0


def test_new_public_lead_gets_crm_defaults(client, admin_client):
    r = client.post("/api/leads", json={
        "name": "Normalize Test", "phone": "+998 90 111-22-33",
        "project_type": "ai", "message": "Salom, g'oyam bor",
    })
    assert r.status_code == 201
    lead_id = r.json()["id"]
    assert lead_id != 0

    r = admin_client.get(f"/api/admin/crm/leads/{lead_id}")
    assert r.status_code == 200
    d = r.json()
    assert d["stage"] == "new"
    assert d["source"] == "website"
    assert d["contact_normalized"] == "+998901112233"
    assert d["contact_type"] == "phone"


def test_duplicate_lead_not_created_twice(client):
    payload = {"name": "Dup Test", "phone": "+998901234000", "project_type": "web", "message": "Birinchi"}
    r1 = client.post("/api/leads", json=payload)
    assert r1.status_code == 201
    id1 = r1.json()["id"]

    payload2 = dict(payload, message="Ikkinchi (qayta ariza)")
    r2 = client.post("/api/leads", json=payload2)
    assert r2.status_code == 201
    id2 = r2.json()["id"]
    assert id1 == id2  # yangi Lead yaratilmagan


def test_stage_transition_creates_history(admin_client):
    r = admin_client.post("/api/admin/crm/leads", json={"name": "Stage Test", "phone": "+998901234111"})
    assert r.status_code == 201
    lead_id = r.json()["id"]

    r = admin_client.patch(f"/api/admin/crm/leads/{lead_id}/stage", json={"stage": "in_work"})
    assert r.status_code == 200
    assert r.json()["stage"] == "in_work"

    r = admin_client.get(f"/api/admin/crm/leads/{lead_id}")
    hist = r.json()["history"]
    assert any(h["from_stage"] == "new" and h["to_stage"] == "in_work" for h in hist)


def test_invalid_stage_rejected(admin_client):
    r = admin_client.post("/api/admin/crm/leads", json={"name": "Bad Stage", "phone": "+998901234555"})
    lead_id = r.json()["id"]
    r = admin_client.patch(f"/api/admin/crm/leads/{lead_id}/stage", json={"stage": "not_a_real_stage"})
    assert r.status_code == 422


def test_manager_sees_only_own_leads_and_is_blocked_from_admin_actions(
    client, admin_client, make_account, login_as, test_password,
):
    # Super admin bitta mijoz yaratadi va manejerga biriktirmaydi
    r = admin_client.post("/api/admin/crm/leads", json={"name": "Not Mine", "phone": "+998901234222"})
    unassigned_id = r.json()["id"]

    make_account("manager1@test.local", test_password, role="manager")
    mgr = login_as("manager1@test.local", test_password)

    # Ko'rish — faqat o'ziga biriktirilganlar (bu yerda hech narsa yo'q)
    r = mgr.get("/api/admin/crm/leads")
    assert r.status_code == 200
    assert all(l["id"] != unassigned_id for l in r.json())

    # CRM Telegram sozlamalari — FAQAT super admin
    r = mgr.get("/api/admin/crm/telegram")
    assert r.status_code == 403

    # Mas'ul biriktirish — manager qila olmaydi
    r = mgr.patch(f"/api/admin/crm/leads/{unassigned_id}/assign", json={"assigned_to": "manager1@test.local"})
    assert r.status_code == 403

    # Arxivlash/o'chirish — manager qila olmaydi
    r = mgr.delete(f"/api/admin/crm/leads/{unassigned_id}")
    assert r.status_code == 403

    # Rolini ko'rish — hisobida to'g'ri qaytishi kerak
    r = mgr.get("/api/admin/account")
    assert r.json()["role"] == "manager"


def test_admin_can_assign_but_not_archive(admin_client, make_account, login_as, test_password):
    r = admin_client.post("/api/admin/crm/leads", json={"name": "Assign Test", "phone": "+998901234333"})
    lead_id = r.json()["id"]

    make_account("admin2@test.local", test_password, role="admin")
    adm = login_as("admin2@test.local", test_password)

    r = adm.patch(f"/api/admin/crm/leads/{lead_id}/assign", json={"assigned_to": "admin2@test.local"})
    assert r.status_code == 200
    assert r.json()["assigned_to"] == "admin2@test.local"

    # Arxivlash — spec bo'yicha FAQAT super admin, admin ham 403 olishi kerak
    r = adm.delete(f"/api/admin/crm/leads/{lead_id}")
    assert r.status_code == 403


def test_only_superadmin_can_promote_role(admin_client, make_account, login_as, test_password):
    make_account("promoteme@test.local", test_password, role="manager")

    # Super admin — ruxsat bor
    r = admin_client.patch(
        "/api/admin/crm/accounts/promoteme@test.local/role", json={"role": "admin"}
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"

    # Endi admin bo'lgan hisobning o'zi boshqa birovni admin qila olmasligi kerak
    make_account("target@test.local", test_password, role="manager")
    adm = login_as("promoteme@test.local", test_password)
    r = adm.patch("/api/admin/crm/accounts/target@test.local/role", json={"role": "admin"})
    assert r.status_code == 403


def test_crmstage_telegram_callback_updates_stage(admin_client):
    """5.3-bo'lim: Telegram inline tugmasi bosilganda Kanban ham yangilanadi."""
    r = admin_client.post("/api/admin/crm/leads", json={"name": "CB Test", "phone": "+998901234444"})
    lead_id = r.json()["id"]

    async def _run():
        from app.telegram import bot
        cq = {
            "id": "cbid1",
            "data": f"crmstage:{lead_id}:contacted",
            "from": {"first_name": "Sinov"},
            "message": {"chat": {"id": -100999}, "message_id": 42},
        }
        await bot._handle_crmstage_callback(cq)

    asyncio.run(_run())
    r = admin_client.get(f"/api/admin/crm/leads/{lead_id}")
    assert r.json()["stage"] == "contacted"


class _FakeBot:
    """crm_service Telegram-sinxronizatsiyasini tarmoqqa chiqmasdan sinash uchun."""

    def __init__(self):
        self.token = "fake-token"
        self.calls: list[str] = []
        self.edit_should_fail_deleted = False

    async def call(self, method, payload=None, timeout=None):
        self.calls.append(method)
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 999}}
        if method == "editMessageText":
            if self.edit_should_fail_deleted:
                return {"ok": False, "description": "Bad Request: message to edit not found"}
            return {"ok": True}
        return {"ok": True}


def test_telegram_sync_sends_once_then_edits_not_resends():
    async def _run():
        from app import crm_service
        from app.db import Lead, SessionLocal

        fake_bot = _FakeBot()
        async with SessionLocal() as s:
            lead = Lead(name="TG Sync", phone="+998901234666", stage="new")
            s.add(lead)
            await s.commit()
            lead_id = lead.id
            tg = await crm_service.get_telegram_settings(s)
            tg.is_enabled = True
            tg.leads_chat_id = "-100123456"
            await s.commit()

        await crm_service.sync_lead_to_telegram(fake_bot, lead_id)
        assert fake_bot.calls == ["sendMessage"]

        async with SessionLocal() as s:
            lead = await s.get(Lead, lead_id)
            assert lead.tg_message_id == 999
            assert lead.tg_sync_state == "synced"

        # Bosqich o'zgardi -> qayta sinxron -> EDIT chaqirilishi kerak, YANGI xabar EMAS
        fake_bot.calls.clear()
        async with SessionLocal() as s:
            lead = await s.get(Lead, lead_id)
            await crm_service.change_stage(s, lead, "in_work", changed_by=None)
        await crm_service.sync_lead_to_telegram(fake_bot, lead_id)
        assert fake_bot.calls == ["editMessageText"]

    asyncio.run(_run())


def test_telegram_resend_when_message_deleted():
    async def _run():
        from app import crm_service
        from app.db import Lead, SessionLocal

        fake_bot = _FakeBot()
        fake_bot.edit_should_fail_deleted = True
        async with SessionLocal() as s:
            lead = Lead(
                name="Deleted Msg", phone="+998901234777", stage="new",
                tg_message_id=111, tg_chat_id="-100123456",
            )
            s.add(lead)
            tg = await crm_service.get_telegram_settings(s)
            tg.is_enabled = True
            tg.leads_chat_id = "-100123456"
            await s.commit()
            lead_id = lead.id

        await crm_service.sync_lead_to_telegram(fake_bot, lead_id)
        assert "editMessageText" in fake_bot.calls
        assert "sendMessage" in fake_bot.calls  # o'chirilgan xabar -> qayta yuborildi

    asyncio.run(_run())


def test_csv_export_blocked_for_manager(make_account, login_as, test_password):
    make_account("csvmgr@test.local", test_password, role="manager")
    mgr = login_as("csvmgr@test.local", test_password)
    r = mgr.get("/api/admin/crm/leads/export.csv")
    assert r.status_code == 403


def test_csv_export_works_for_admin(admin_client):
    r = admin_client.get("/api/admin/crm/leads/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "id,name,phone" in r.text.replace("﻿", "")


def test_stats_endpoint_reachable(admin_client):
    r = admin_client.get("/api/admin/crm/stats")
    assert r.status_code == 200
    d = r.json()
    assert "funnel" in d and "conversion_pct" in d


def test_add_account_with_role_sets_role_on_activation(admin_client):
    """Superadmin yangi hisob qo'shayotganda rolni ('admin'/'manager') tanlay
    olishi va tasdiqlangach shu rol o'rnatilishi kerak."""
    r = admin_client.post("/api/admin/account/emails/request-add", json={
        "new_email": "newsotuv@test.local",
        "password": "NewSotuv123!",
        "confirm_password": "NewSotuv123!",
        "role": "admin",
    })
    assert r.status_code == 200

    async def _latest_add_email_token():
        from sqlalchemy import select
        from app.db import AdminToken, SessionLocal
        async with SessionLocal() as s:
            row = await s.scalar(
                select(AdminToken).where(AdminToken.purpose == "add_email")
                .order_by(AdminToken.created_at.desc())
            )
            return row.token

    token = asyncio.run(_latest_add_email_token())
    r = admin_client.post("/api/auth/confirm-token", json={"token": token})
    assert r.status_code == 200
    assert r.json()["email"] == "newsotuv@test.local"

    r = admin_client.get("/api/admin/account")
    acc = next(a for a in r.json()["accounts"] if a["email"] == "newsotuv@test.local")
    assert acc["role"] == "admin"
