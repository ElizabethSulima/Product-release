from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BatchExternalCreate(BaseModel):
    """
    Схема входящего запроса на создание партии (с русскими полями)
    """

    model_config = ConfigDict(populate_by_name=True)

    status_closing: bool = Field(
        default=False, alias="СтатусЗакрытия", description="Статус закрытия"
    )
    task_description: str = Field(
        alias="ПредставлениеЗаданияНаСмену", description="Описание задания"
    )
    work_center_name: str = Field(
        alias="РабочийЦентр", description="Название рабочего центра"
    )
    shift: str = Field(alias="Смена", description="Смена")
    team: str = Field(alias="Бригада", description="Бригада")
    batch_number: int = Field(alias="НомерПартии", description="Номер партии")
    batch_date: date = Field(alias="ДатаПартии", description="Дата партии")
    nomenclature: str = Field(alias="Номенклатура", description="Номенклатура")
    ekn_code: str = Field(alias="КодЕКН", description="Код ЕКН")
    work_center_id: str = Field(
        alias="ИдентификаторРЦ", description="Идентификатор рабочего центра"
    )
    shift_start: datetime = Field(
        alias="ДатаВремяНачалаСмены", description="Начало смены"
    )
    shift_end: datetime = Field(
        alias="ДатаВремяОкончанияСмены", description="Окончание смены"
    )

    @model_validator(mode="after")
    def validate_shift_times(self) -> "BatchExternalCreate":
        if self.shift_end <= self.shift_start:
            raise ValueError(
                "ДатаВремяОкончанияСмены должна быть позже ДатаВремяНачалаСмены"
            )
        return self


class BatchBase(BaseModel):
    """
    Базовая схема с общими полями для создания и обновления
    """

    task_description: str
    work_center_id: int
    shift: str = Field(max_length=100, description="Название или номер смены")
    team: str = Field(max_length=100, description="Название или номер бригады")

    batch_number: int = Field(description="Номер партии")
    batch_date: date = Field(description="Дата партии")
    nomenclature: str = Field(max_length=255, description="Номенклатура")
    ekn_code: str = Field(max_length=100, description="Код ЕКН")

    shift_start: datetime = Field(description="Начало смены")
    shift_end: datetime = Field(description="Конец смены")

    @model_validator(mode="after")
    def validate_shift_times(self) -> "BatchBase":
        """Проверка, что конец смены позже начала."""
        if self.shift_end <= self.shift_start:
            raise ValueError(
                "Время окончания смены (shift_end) должно быть позже времени начала (shift_start)"
            )
        return self


class BatchCreate(BatchBase):
    """
    Схема для создания новой производственной партии
    """

    is_closed: bool = Field(default=False, description="Закрыта ли партия")
    closed_at: datetime | None = Field(
        default=None, description="Время закрытия партии"
    )


class BatchUpdate(BaseModel):
    """
    Схема для обновления партии
    """

    task_description: str | None = None
    work_center_id: int | None = None
    shift: str | None = Field(default=None, max_length=100)
    team: str | None = Field(default=None, max_length=100)

    batch_number: int | None = None
    batch_date: date | None = None
    nomenclature: str | None = Field(default=None, max_length=255)
    ekn_code: str | None = Field(default=None, max_length=100)

    shift_start: datetime | None = None
    shift_end: datetime | None = None
    is_closed: bool | None = None
    closed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_shift_times(self) -> "BatchUpdate":
        """Проверка времени смены, если переданы оба значения"""
        if (
            self.shift_start
            and self.shift_end
            and self.shift_end <= self.shift_start
        ):
            raise ValueError(
                "Время окончания смены должно быть позже времени начала"
            )
        return self


class BatchResponse(BaseModel):
    """
    Схема для ответа клиенту
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_closed: bool
    closed_at: datetime | None
    task_description: str
    work_center_id: int
    shift: str
    team: str
    batch_number: int
    batch_date: date
    nomenclature: str
    ekn_code: str
    shift_start: datetime
    shift_end: datetime
    created_at: datetime
    updated_at: datetime
