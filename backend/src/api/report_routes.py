import io
import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database.db import get_db
from ..database.models import User, Device, AuditLog, TelemetryLog
from .auth_routes import get_current_user

# ReportLab imports
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
except ImportError:
    pass

router = APIRouter(prefix="/api", tags=["Reports & Audit"])

class AuditLogCreate(BaseModel):
    device_id: str
    action_type: str
    reason: str
    details: dict = {}

@router.post("/audit/log")
async def create_audit_log(
    payload: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra uma ação no log de auditoria (ex: Reconhecer Alarme)"""
    new_log = AuditLog(
        user_id=current_user.id,
        device_id=payload.device_id,
        action_type=payload.action_type,
        reason=payload.reason,
        details=json.dumps(payload.details) if payload.details else None
    )
    db.add(new_log)
    await db.commit()
    return {"success": True, "message": "Ação registrada com sucesso na auditoria."}

@router.get("/reports/pdf")
async def generate_pdf_report(
    device_id: str = Query(None, description="ID opcional do dispositivo"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera um relatório de conformidade em PDF imutável."""
    # Busca os dispositivos do usuário
    if device_id:
        dev_query = select(Device).where(Device.user_id == current_user.id, Device.id == device_id)
    else:
        dev_query = select(Device).where(Device.user_id == current_user.id)
        
    devices_result = await db.execute(dev_query)
    devices = devices_result.scalars().all()
    
    if not devices:
        raise HTTPException(status_code=404, detail="Nenhum dispositivo encontrado para relatório.")

    # Busca logs de auditoria recentes (últimas 24h para o exemplo)
    audit_query = select(AuditLog).where(
        AuditLog.user_id == current_user.id
    ).order_by(AuditLog.created_at.desc()).limit(20)
    audit_result = await db.execute(audit_query)
    audits = audit_result.scalars().all()

    # Criação do PDF em memória
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Cabeçalho
    elements.append(Paragraph(f"Relatório de Conformidade - {datetime.date.today().strftime('%d/%m/%Y')}", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Usuário: {current_user.email}", normal_style))
    elements.append(Paragraph("Este documento é gerado automaticamente e reflete o estado dos equipamentos monitorados.", normal_style))
    elements.append(Spacer(1, 20))
    
    # Tabela de Status de Freezers
    elements.append(Paragraph("Status Atual dos Equipamentos", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    table_data = [["Nome/Local", "Temp Atual", "Status", "Bateria"]]
    for d in devices:
        t_atual = f"{d.current_temp:.1f}°C" if d.current_temp is not None else "--"
        bat = f"{d.battery_level}%" if d.battery_level is not None else "--"
        status = d.status or "OFFLINE"
        table_data.append([f"{d.name} ({d.location})", t_atual, status, bat])
        
    t = Table(table_data, colWidths=[200, 100, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Tabela de Logs de Auditoria
    elements.append(Paragraph("Logs de Auditoria (Recentes)", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    audit_data = [["Data/Hora", "Ação", "Motivo"]]
    for a in audits:
        dt = a.created_at.strftime('%d/%m %H:%M') if a.created_at else "--"
        audit_data.append([dt, a.action_type, a.reason or "N/A"])
        
    if len(audit_data) > 1:
        at = Table(audit_data, colWidths=[100, 150, 250])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(at)
    else:
        elements.append(Paragraph("Nenhum registro de auditoria encontrado.", normal_style))
    
    # Gera o PDF
    doc.build(elements)
    
    buffer.seek(0)
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Relatorio_ColdChain_{datetime.date.today().strftime('%Y%m%d')}.pdf"}
    )
