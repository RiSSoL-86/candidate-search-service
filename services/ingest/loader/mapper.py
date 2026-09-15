import uuid
from typing import Any

import schemas
from css_models.enums import EducationType, Gender
from utils import driver_licenses, enum_member


class ResumeMapper:
    """Turns a validated payload into the column values each table wants."""

    def owner(self, resume: schemas.Resume) -> dict[str, Any]:
        """The person card, filled from whichever download reached us first."""
        return {
            "hh_owner_id": resume.owner.id,
            "first_name": resume.first_name,
            "last_name": resume.last_name,
            "middle_name": resume.middle_name,
            "age": resume.age,
            "gender": enum_member(
                Gender, resume.gender.id if resume.gender else None
            ),
            "birth_date": resume.birth_date,
            "contact": resume.contact,
        }

    def area(self, area: schemas.Area) -> dict[str, Any]:
        """The geography card every resume of that city points at."""
        return {
            "hh_area_id": area.id,
            "name": area.name,
            "hh_url": area.url,
        }

    def metro(self, metro: schemas.Metro) -> dict[str, Any]:
        """The metro card, which repeats across thousands of resumes."""
        return {
            "hh_metro_id": metro.id,
            "name": metro.name,
            "lat": metro.lat,
            "lng": metro.lng,
            "hh_order": metro.order,
            "line": metro.line,
        }

    def employer(self, employer: schemas.Employer) -> dict[str, Any]:
        """The company card, shared by every job entry that names it."""
        return {
            "hh_employer_id": employer.id,
            "name": employer.name,
            "hh_url": employer.url,
            "hh_alternate_url": employer.alternate_url,
            "logo_urls": employer.logo_urls,
        }

    def resume(
        self,
        source: schemas.Source,
        resume: schemas.Resume,
        owner_id: uuid.UUID,
        area_id: uuid.UUID | None,
        metro_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        """Spread the payload over the columns, JSONB blocks included."""
        salary = resume.salary
        relocation = resume.relocation

        return {
            "owner_id": owner_id,
            "resume_type": source.resume_type,
            "downloaded_at": source.downloaded_at,
            "s3_bucket": source.bucket,
            "s3_key": source.key,
            "s3_version_id": source.version_id,
            "hh_resume_id": resume.id,
            "hh_real_id": resume.real_id,
            "hh_url": resume.url,
            "hh_alternate_url": resume.alternate_url,
            "hh_created_at": resume.created_at,
            "hh_updated_at": resume.updated_at,
            "platform_id": resume.platform.id if resume.platform else None,
            "title": resume.title,
            "salary_amount": salary.amount if salary else None,
            "salary_currency": salary.currency if salary else None,
            "total_experience_months": (
                resume.total_experience.months
                if resume.total_experience
                else None
            ),
            "skill_set": resume.skill_set,
            "skills": resume.skills,
            "photo": resume.photo,
            "area_id": area_id,
            "metro_id": metro_id,
            "education_level": (
                resume.education.level if resume.education else None
            ),
            "job_search_status": resume.job_search_status,
            "business_trip_readiness": resume.business_trip_readiness,
            "travel_time": resume.travel_time,
            "resume_locale": resume.resume_locale,
            "relocation_type": relocation.type if relocation else None,
            "relocation_area": relocation.area if relocation else None,
            "relocation_district": relocation.district if relocation else None,
            "employments": resume.employments,
            "schedules": resume.schedules,
            "employment_form": resume.employment_form,
            "work_format": resume.work_format,
            "professional_roles": resume.professional_roles,
            "citizenship": resume.citizenship,
            "work_ticket": resume.work_ticket,
            "language": resume.language,
            "portfolio": resume.portfolio,
            "certificate": resume.certificate,
            "site": resume.site,
            "recommendation": resume.recommendation,
            "hidden_fields": resume.hidden_fields,
            "tags": resume.tags,
            "driver_license_types": driver_licenses(
                resume.driver_license_types
            ),
            "has_vehicle": resume.has_vehicle,
            "has_medical_book": resume.has_medical_book,
            "has_self_employment": resume.has_self_employment,
        }

    def experience(
        self,
        resume_id: uuid.UUID,
        entry: schemas.Experience,
        employer_id: uuid.UUID | None,
        area_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        """One job of this download, tied to the snapshot that listed it."""
        return {
            "resume_id": resume_id,
            "hh_experience_id": entry.id,
            "company": entry.company,
            "hh_company_id": entry.company_id,
            "company_url": entry.company_url,
            "employer_id": employer_id,
            "position": entry.position,
            "start_date": entry.start,
            "end_date": entry.end,
            "description": entry.description,
            "area_id": area_id,
            "industry": entry.industry,
            "industries": entry.industries,
        }

    def education(
        self,
        resume_id: uuid.UUID,
        entry: schemas.Education,
        education_type: EducationType,
    ) -> dict[str, Any]:
        """One study entry, with the HH bucket it was listed under."""
        return {
            "resume_id": resume_id,
            "hh_education_id": entry.id,
            "education_type": education_type,
            "education_level": entry.education_level,
            "name": entry.name,
            "organization": entry.organization,
            "result": entry.result,
            "year": entry.year,
            "university_acronym": entry.university_acronym,
            "hh_name_id": entry.name_id,
            "hh_organization_id": entry.organization_id,
            "hh_result_id": entry.result_id,
        }
