-- Dados FICTÍCIOS para demonstração. Senha de todos os veterinários: Senha@123
INSERT INTO especie (nome, descricao) VALUES ('Cão','Canis lupus familiaris'),('Gato','Felis catus'),('Ave','Aves domésticas');
INSERT INTO raca (id_especie, nome, porte) VALUES
 (1,'Labrador','Grande'),(1,'Poodle','Pequeno'),(1,'Shih Tzu','Pequeno'),
 (2,'Siamês','Médio'),(2,'Persa','Médio'),(3,'Calopsita','Pequeno');

INSERT INTO veterinario (nome,cpf,crmv,crmv_uf,telefone,email,senha_hash,senha_confirmada,confirmada_em,situacao) VALUES
 ('Dra. Ana Souza','11144477735','12345','RJ','21999990001','ana.souza@clinica.test','scrypt:32768:8:1$JEUaGHM0RY2YKWsE$35aca5a108d8dfbc0042d068fa1691d324069eb3ef138787aea4cee7ccbf7b1eeef5db68fae375605c7d6a9cd94fc2b93e666925a80dbd24ec5c75ada0c31d23',1,datetime('now'),'ATIVO'),
 ('Dr. Bruno Lima (INATIVO)','52998224725','23456','RJ','21999990002','bruno.lima@clinica.test','scrypt:32768:8:1$JEUaGHM0RY2YKWsE$35aca5a108d8dfbc0042d068fa1691d324069eb3ef138787aea4cee7ccbf7b1eeef5db68fae375605c7d6a9cd94fc2b93e666925a80dbd24ec5c75ada0c31d23',1,datetime('now'),'INATIVO');
INSERT INTO veterinario (nome,cpf,crmv,crmv_uf,telefone,email,senha_hash,senha_confirmada,codigo_confirmacao,situacao) VALUES
 ('Dra. Carla Dias (SENHA NÃO CONFIRMADA)','12345678909','34567','RJ','21999990003','carla.dias@clinica.test','scrypt:32768:8:1$JEUaGHM0RY2YKWsE$35aca5a108d8dfbc0042d068fa1691d324069eb3ef138787aea4cee7ccbf7b1eeef5db68fae375605c7d6a9cd94fc2b93e666925a80dbd24ec5c75ada0c31d23',0,'123456','ATIVO');

INSERT INTO endereco (cep,logradouro,numero,complemento,bairro,cidade,uf,codigo_ibge) VALUES
 ('20040020','Rua da Assembleia','10','Sala 1','Centro','Rio de Janeiro','RJ','3304557');
INSERT INTO tutor (id_endereco,nome,cpf,data_nascimento,telefone,email) VALUES
 (1,'Maria Fictícia da Silva','98765432100','1990-05-20','21988880000','maria.ficticia@exemplo.test');
INSERT INTO animal (id_tutor,id_especie,id_raca,nome,data_nascimento,sexo,cor,peso_atual) VALUES
 (1,1,2,'Thor','2021-03-10','M','Caramelo',8.5);
