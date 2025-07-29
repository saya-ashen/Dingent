import enum
import urllib.parse
from typing import cast

from pydantic import computed_field, field_validator
from sqlmodel import Field, Relationship, SQLModel


class Group(str, enum.Enum):
    TOY = "Toy Group"
    HOUND = "Hound Group"
    TERRIER = "Terrier Group"
    WORKING = "Working Group"
    NON_SPORTING = "Non-Sporting Group"
    SPORTING = "Sporting Group"
    FSS = "FSS"
    HERDING = "Herding Group"
    MISCELLANEOUS = "Miscellaneous"
    EXTINCT = "extinct"


class BreedDiseaseAssociation(SQLModel, table=True):
    __tablename__ = "breed_associate_disease"  # type: ignore
    breed_id: int = Field(..., primary_key=True, foreign_key="breed.breed_id", description="Breed unique identify")
    disease_id: str = Field(
        ..., primary_key=True, foreign_key="general_disease_annotate.disease_id", description="Disease unique identify"
    )
    affect_level: str | None = Field(None)


class DiseaseGeneAssociation(SQLModel, table=True):
    __tablename__ = "disease_map_omia"  # type: ignore
    omia_id: int = Field(..., primary_key=True, foreign_key="omia_map_gene.omia_id", description="Gene unique identify")
    disease_id: str = Field(
        ..., primary_key=True, foreign_key="general_disease_annotate.disease_id", description="Disease unique identify"
    )


class Breed(SQLModel, table=True):
    __tablename__ = "breed"  # type: ignore
    __table_args__ = ({"info": {"title": "品种", "must_queried_columns": ["breed_id", "src_breed_name"]}},)

    breed_id: int = Field(
        ...,
        primary_key=True,
        description="Gene unique identify",
    )
    src_breed_name: str = Field(
        "",
        alias="物种名称",
        description="full name of breed in English. ",
    )

    @field_validator("src_breed_name")
    @classmethod
    def add_breed_link(cls, v):
        link_pattern = f"https://ngdc.cncb.ac.cn/idog/dogph/breed/getBreedDetailByName.action?name={v}"
        markdown_link = f"[{v}]({urllib.parse.quote(link_pattern, safe=':/?=')})"
        return markdown_link



    breed_group: str | None = Field(None, description="breed group")
    general_appearance: str | None = Field(
        None,
        alias="外貌",
        description="狗的整体外貌特征，可能包含很多种特征描述，如果用户的问题在其他字段无法找到，可以在此字段中查找。",
    )
    personality: str | None = Field(None, alias="性格", description="personality of breed")
    energy_level: str | None = Field(None, description="energy level of breed")
    good_with_children: str | None = Field(
        None, alias="对儿童友好", description="是否对儿童友好，yes or no or 'Better with Supervision'"
    )
    shedd: str | None = Field(None, description="掉毛程度，包括：Seasonal,Infrequent,Occasional")
    groom: str | None = Field(None, description="dog grooming level")
    train: str | None = Field(
        None,
        description="The dog's willingness to train, e.g.: 'Eager To Please' Independent 'Responds Well' Agreeable 'May be Stubborn' 'Easy Training'",
    )
    min_life: str | None = Field(None, description="最小寿命")
    max_life: str | None = Field(None, description="最大寿命")
    diseases: list["Disease"] = Relationship(back_populates="breeds", link_model=BreedDiseaseAssociation)
    original: str | None = Field(None, alias="原产地", description="原产地国家")
    colors: str | None = Field(None, alias="颜色", description="颜色")

    @computed_field(alias="疾病名称")
    @property
    def breed_diseases(self) -> str:
        return ",".join([disease.disease_name for disease in self.diseases])


class Disease(SQLModel, table=True):
    __tablename__ = "general_disease_annotate"  # type: ignore
    __table_args__ = (
        {"info": {"title": "疾病", "must_queried_columns": ["disease_id", "disease_name", "disease_desc"]}},
    )

    disease_id: str = Field(..., primary_key=True, max_length=10, description="疾病唯一标识，用作外键")
    disease_name: str = Field(
        ...,
        alias="疾病名称",
        description="犬品种疾病名称（英文）",
    )

    @field_validator("disease_name")
    @classmethod
    def add_breed_link(cls, v):
        link_pattern = f"https://ngdc.cncb.ac.cn/idog/dogph/disease/getDiseaseDetailByName.action?name={v}"
        markdown_link = f"[{v}]({urllib.parse.quote(link_pattern, safe=':/?=')})"
        return markdown_link

    disease_desc: str | None = Field(default=None, alias="疾病描述", description="疾病描述（英文）")
    trait_method: str | None = Field(default=None, alias="治疗方法", description="疾病治疗方法（英文）")
    disease_diagnose: str | None = Field(default=None, alias="疾病诊断", description="疾病诊断（英文）")
    disease_trait: str | None = Field(default=None, alias="疾病症状", description="疾病症状（英文）")
    disease_cause: str | None = Field(default=None, alias="疾病原因", description="犬品种疾病原因（英文）")
    breeder_advice: str | None = Field(default=None, alias="饲养建议", description="犬主饲养建议（英文）")
    breeds: list["Breed"] = Relationship(back_populates="diseases", link_model=BreedDiseaseAssociation)
    genes: list["Gene"] = Relationship(back_populates="diseases", link_model=DiseaseGeneAssociation)

    @computed_field(alias="物种名称")
    @property
    def disease_breeds(self) -> str:
        return ",".join([breed.src_breed_name for breed in self.breeds])

    @computed_field(alias="基因名称")
    @property
    def disease_genes(self) -> str:
        return ",".join([gene.gene_symbol for gene in self.genes])


class Gene(SQLModel, table=True):
    __tablename__ = "omia_map_gene"  # type: ignore
    __table_args__ = ({"info": {"title": "基因", "must_queried_columns": ["gene_symbol"]}},)

    omia_id: int = Field(..., primary_key=True, description="Gene unique identify")
    gene_symbol: str = Field(
        "",
        alias="基因名称",
        description="a standardized, abbreviated representation of a gene's name",
    )
    gene_desc: str | None = Field(None, alias="基因描述", description="the full description of gene symbol")
    diseases: list["Disease"] = Relationship(back_populates="genes", link_model=DiseaseGeneAssociation)

    @computed_field(alias="疾病名称")
    @property
    def gene_diseases(self) -> str:
        return ",".join([disease.disease_name for disease in self.diseases])


def summarize_data(data: dict[str, list[SQLModel]]) -> str:
    summary_data = {
        "breed_count": None,
        "disease_count": None,
        "gene_count": None,
        "gene_head_10": [],
        "disease_head_10": [],
        "breed_head_10": [],
    }
    summary_data["diseases_count"] = len(data.get("general_disease_annotate", []))
    summary_data["breed_count"] = len(data.get("breed_view", []))
    summary_data["gene_count"] = len(data.get("omia_map_gene", []))

    breed_names = [cast(Breed, breed).src_breed_name for breed in data.get("breed_view", [])]
    gene_names = [cast(Gene, gene).gene_symbol for gene in data.get("omia_map_gene", [])]
    disease_names = [cast(Disease, disease).disease_name for disease in data.get("general_disease_annotate", [])]
    summary_text = f"共分析了{summary_data['breed_count']}个品种，{summary_data['diseases_count']}个疾病，{summary_data['gene_count']}个基因。\n\n"
    summary_text += "前10个品种、基因和疾病名称如下：\n\n"
    summary_text += f"品种名称：{', '.join(breed_names[:10])}\n\n"
    summary_text += f"基因名称：{', '.join(gene_names[:10])}\n\n"
    summary_text += f"疾病名称：{', '.join(disease_names[:10])}\n\n"

    return summary_text
